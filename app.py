"""ModFerry: local batch uploader for CurseForge and Modrinth. Run: python app.py"""
import json
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Flask, g, jsonify, request, send_from_directory

from file_inspect import EXTENSIONS, PROJECT_TYPES, inspect_upload, platforms_for
from markdown_preview import render as render_markdown
from messages import UserError, pick_lang, t
from secrets_store import TokenStore
from version import VERSION

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('MODFERRY_DATA') or os.environ.get('CF_UPLOADER_DATA') or ROOT / 'data')
DATA.mkdir(parents=True, exist_ok=True)
FILES = DATA / 'files'
FILES.mkdir(exist_ok=True)
PROFILES = DATA / 'profiles.json'
HISTORY = DATA / 'history.json'
TOKENS = TokenStore(DATA)
APP_HOST = '127.0.0.1'
APP_PORT = int(os.environ.get('MODFERRY_PORT', '8765'))
MAX_FILE_MB = 500
MAX_FILE = MAX_FILE_MB * 1024 * 1024
USER_AGENT = f'ModFerry/{VERSION} (local batch uploader)'
CF_API = 'https://minecraft.curseforge.com/api'
MR_API = 'https://api.modrinth.com/v2'

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024
files_lock = threading.RLock()
file_index = {}
jobs = {}
jobs_lock = threading.Lock()
history_lock = threading.Lock()
version_cache = {'at': 0, 'token': None, 'payload': None}

CONTENT_TYPES = {'.jar': 'application/java-archive', '.zip': 'application/zip',
                 '.mrpack': 'application/x-modrinth-modpack+zip'}
# CurseForge website class slugs, used for links when the project slug is known.
CF_CLASSES = {'mod': 'mc-mods', 'resourcepack': 'texture-packs', 'datapack': 'data-packs',
              'shader': 'shaders', 'modpack': 'modpacks'}
RELEASE_TYPES = ('release', 'beta', 'alpha')


# ---------------------------------------------------------------- helpers

def lang():
    return getattr(g, 'lang', 'en')


def api_error(message, code=400):
    return jsonify(error=message), code


def user_error(exc, code=400):
    if isinstance(exc, UserError):
        return api_error(exc.text(lang()), code)
    return api_error(str(exc), code)


def write_json(path, payload):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), 'utf-8')
    temporary.replace(path)


def read_json(path, default):
    try:
        return json.loads(path.read_text('utf-8')) if path.exists() else default
    except (OSError, json.JSONDecodeError):
        return default


def clean_cache():
    """The file index lives in memory, so every cached file is orphaned after a restart."""
    removed = 0
    for item in FILES.iterdir():
        if item.is_file():
            try:
                item.unlink()
                removed += 1
            except OSError:
                pass
    return removed


def project_type(data):
    kind = data.get('projectType', 'mod')
    if kind not in PROJECT_TYPES:
        raise UserError('err.projectType')
    return kind


def saved_token(platform, supplied=''):
    if supplied:
        return str(supplied).strip()
    return str(TOKENS.read().get(platform, '')).strip()


def stored_files():
    with files_lock:
        return dict(file_index)


def cf_link(kind, project, slug, file_id):
    if slug and re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,99}', slug):
        return f'https://www.curseforge.com/minecraft/{CF_CLASSES[kind]}/{slug}/files/{file_id}'
    return f'https://www.curseforge.com/projects/{project}'


def mr_link(project_id, version_id):
    return f'https://modrinth.com/project/{project_id}/version/{version_id}'


def add_history(entry):
    with history_lock:
        items = read_json(HISTORY, [])
        if not isinstance(items, list):
            items = []
        items.insert(0, entry)
        write_json(HISTORY, items[:1000])


# ---------------------------------------------------------------- guards

@app.before_request
def local_only_guard():
    g.lang = pick_lang(request.headers.get('X-ModFerry-Lang'), request.headers.get('Accept-Language', ''))
    # Other websites and DNS rebinding must not control this localhost server.
    host = request.host.split(':', 1)[0]
    if host not in ('127.0.0.1', 'localhost'):
        return api_error(t('err.localOnly', lang()), 403)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('Origin', '')
        if origin:
            parsed = urlparse(origin)
            if parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.port != APP_PORT or parsed.scheme != 'http':
                return api_error(t('err.badOrigin', lang()), 403)


@app.get('/')
def index():
    return send_from_directory('static', 'index.html')


@app.get('/api/info')
def info():
    return jsonify(version=VERSION, projectTypes=list(PROJECT_TYPES),
                   extensions={k: {ext: list(p) for ext, p in v.items()} for k, v in EXTENSIONS.items()},
                   maxFileMb=MAX_FILE_MB)


# ---------------------------------------------------------------- tokens

@app.get('/api/tokens')
def token_status():
    return jsonify(TOKENS.status())


@app.post('/api/tokens/unlock')
def token_unlock():
    try:
        TOKENS.unlock((request.get_json(silent=True) or {}).get('password', ''))
        return jsonify(TOKENS.status())
    except (ValueError, OSError) as exc:
        return user_error(exc)


@app.post('/api/tokens')
def token_save():
    body = request.get_json(silent=True) or {}
    if any(k not in ('curseforge', 'modrinth') for k in body):
        return api_error(t('err.tokenField', lang()))
    try:
        saved = TOKENS.read()
        for key, value in body.items():
            if not isinstance(value, str):
                return api_error(t('err.tokenText', lang()))
            if value.strip():
                saved[key] = value.strip()
        TOKENS.write(saved)
        return jsonify(TOKENS.status())
    except (ValueError, OSError) as exc:
        return user_error(exc)


@app.delete('/api/tokens/<platform>')
def token_delete(platform):
    if platform not in ('curseforge', 'modrinth'):
        return api_error(t('err.platform', lang()))
    try:
        saved = TOKENS.read()
        saved.pop(platform, None)
        TOKENS.write(saved)
        return jsonify(TOKENS.status())
    except (ValueError, OSError) as exc:
        return user_error(exc)


# ---------------------------------------------------------------- CurseForge versions

def normalize_items(obj):
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ('data', 'versions', 'gameVersions'):
            if isinstance(obj.get(key), list):
                return obj[key]
    return []


def get_versions(token):
    cached = version_cache['payload']
    if cached and version_cache['token'] == token and time.time() - version_cache['at'] < 3600:
        return cached
    headers = {'X-Api-Token': token, 'Accept': 'application/json', 'User-Agent': USER_AGENT}
    resp = requests.get(CF_API + '/game/versions', headers=headers, timeout=35)
    resp.raise_for_status()
    versions = normalize_items(resp.json())
    if not versions:
        raise UserError('err.versionsEmpty')
    clean = []
    for v in versions:
        try:
            clean.append({'id': int(v['id']), 'name': str(v['name']), 'typeId': int(v.get('gameVersionTypeID', 0))})
        except (ValueError, TypeError, KeyError):
            continue
    types = []
    try:
        r = requests.get(CF_API + '/game/version-types', headers=headers, timeout=25)
        if r.ok:
            for item in normalize_items(r.json()):
                try:
                    types.append({'id': int(item['id']), 'name': str(item.get('name', '')), 'slug': str(item.get('slug', ''))})
                except (KeyError, ValueError, TypeError):
                    continue
    except requests.RequestException:
        pass
    result = {'versions': clean, 'types': types}
    version_cache.update(payload=result, at=time.time(), token=token)
    return result


def classify(v, types):
    """Never classify an ambiguous numeric name as Minecraft without its type metadata."""
    n = v['name'].strip().lower()
    info = types.get(v['typeId'], {})
    slug = info.get('slug', '').lower()
    text = (info.get('name', '') + ' ' + slug).lower()
    if 'modloader' in slug or 'mod loader' in text or n in ('neoforge', 'forge', 'fabric', 'quilt', 'rift', 'liteloader'):
        return 'loader'
    if 'java' in text or re.fullmatch(r'java\s*\d+', n):
        return 'java'
    if 'environment' in text or 'side' in text or n in ('client', 'server'):
        return 'environment'
    if slug.startswith('minecraft') or ('minecraft' in text and 'modloader' not in text):
        return 'minecraft'
    return 'other'


@app.post('/api/versions')
def versions_endpoint():
    try:
        token = saved_token('curseforge', (request.get_json(silent=True) or {}).get('token', ''))
    except (ValueError, OSError) as exc:
        return user_error(exc)
    if not token:
        return api_error(t('err.cfTokenMissing', lang()))
    try:
        payload = get_versions(token)
        typemap = {item['id']: item for item in payload['types']}
        return jsonify(versions=[dict(v, category=classify(v, typemap),
                                      typeName=typemap.get(v['typeId'], {}).get('name', ''),
                                      typeSlug=typemap.get(v['typeId'], {}).get('slug', ''))
                                 for v in payload['versions']])
    except UserError as exc:
        return user_error(exc, 502)
    except (requests.RequestException, ValueError) as exc:
        return api_error(t('err.versionsFailed', lang(), detail=str(exc)), 502)


# ---------------------------------------------------------------- Modrinth tags

@app.get('/api/modrinth-tags')
def modrinth_tags():
    try:
        headers = {'User-Agent': USER_AGENT}
        v = requests.get(MR_API + '/tag/game_version', headers=headers, timeout=25)
        loaders = requests.get(MR_API + '/tag/loader', headers=headers, timeout=25)
        v.raise_for_status()
        loaders.raise_for_status()
        return jsonify(gameVersions=[{'version': x['version'], 'type': x.get('version_type', 'release')} for x in v.json()],
                       loaders=[{'name': x['name'], 'types': x.get('supported_project_types', [])} for x in loaders.json()])
    except (requests.RequestException, ValueError, KeyError) as exc:
        return api_error(t('err.mrTags', lang(), detail=str(exc)), 502)


# ---------------------------------------------------------------- files

@app.post('/api/files')
def add_files():
    incoming = request.files.getlist('files')
    if not incoming:
        return api_error(t('err.noFiles', lang()))
    kind = request.form.get('projectType', 'mod')
    if kind not in PROJECT_TYPES:
        return api_error(t('err.projectType', lang()))
    allowed = EXTENSIONS[kind]
    created = []
    for f in incoming:
        name = Path(f.filename or '').name
        suffix = Path(name).suffix.lower()
        if not name or name.startswith('.') or len(name) > 200:
            return api_error(t('err.fileName', lang()))
        if suffix not in allowed and request.form.get('purpose') != 'serverpack':
            return api_error(t('err.fileType', lang(), type=kind, name=name, allowed=', '.join(allowed)))
        if request.form.get('purpose') == 'serverpack' and suffix != '.zip':
            return api_error(t('err.fileType', lang(), type='server pack', name=name, allowed='.zip'))
        fileid = secrets.token_urlsafe(18)
        path = FILES / (fileid + suffix)
        size = 0
        try:
            with path.open('wb') as dest:
                while True:
                    chunk = f.stream.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_FILE:
                        raise UserError('err.fileTooLarge', mb=MAX_FILE_MB, name=name)
                    dest.write(chunk)
            if not size:
                raise UserError('err.fileEmpty', name=name)
        except (UserError, OSError) as exc:
            path.unlink(missing_ok=True)
            return user_error(exc)
        with files_lock:
            file_index[fileid] = {'path': str(path), 'name': name, 'size': size}
        detected = {} if request.form.get('purpose') == 'serverpack' else inspect_upload(path, name, kind)
        created.append({'id': fileid, 'name': name, 'size': size, 'detected': detected})
    return jsonify(files=created)


@app.delete('/api/files/<fileid>')
def remove_file(fileid):
    with files_lock:
        item = file_index.pop(fileid, None)
    if item:
        Path(item['path']).unlink(missing_ok=True)
    return jsonify(ok=True)


# ---------------------------------------------------------------- profiles

PROFILE_KEYS = ('projectType', 'projectId', 'cfSlug', 'modrinthProject', 'publishCF', 'publishMR', 'releaseType',
                'changelog', 'manualRelease', 'mrStatus', 'mrFeatured', 'showSnapshots', 'entries')


@app.get('/api/profiles')
def get_profiles():
    data = read_json(PROFILES, {})
    return jsonify(profiles=data if isinstance(data, dict) else {})


@app.post('/api/profiles')
def save_profile():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    if not 1 <= len(name) <= 80:
        return api_error(t('err.profileName', lang()))
    settings = data.get('settings', {})
    if not isinstance(settings, dict):
        return api_error(t('err.profileInvalid', lang()))
    # Never persist tokens or cached file IDs.
    settings = {k: v for k, v in settings.items() if k in PROFILE_KEYS}
    profiles = get_profiles().json['profiles']
    profiles[name] = settings
    write_json(PROFILES, profiles)
    return jsonify(ok=True)


@app.delete('/api/profiles/<name>')
def delete_profile(name):
    profiles = get_profiles().json['profiles']
    profiles.pop(name, None)
    write_json(PROFILES, profiles)
    return jsonify(ok=True)


# ---------------------------------------------------------------- history

@app.get('/api/history')
def get_history():
    items = read_json(HISTORY, [])
    return jsonify(history=items if isinstance(items, list) else [])


@app.delete('/api/history')
def clear_history():
    with history_lock:
        write_json(HISTORY, [])
    return jsonify(ok=True)


@app.post('/api/markdown-preview')
def markdown_preview_endpoint():
    try:
        return jsonify(html=render_markdown((request.get_json(silent=True) or {}).get('markdown', '')))
    except ValueError as exc:
        return user_error(exc)


# ---------------------------------------------------------------- CurseForge upload

# Values explicitly accepted by the CurseForge author upload endpoint.
UPLOAD_RELATION_TYPES = frozenset(('embeddedLibrary', 'optionalDependency', 'requiredDependency', 'tool', 'incompatible'))
ALL_RELATION_TYPES = UPLOAD_RELATION_TYPES | {'include'}


def validate_relations(relations, filename):
    if not isinstance(relations, list) or len(relations) > 100:
        raise UserError('err.relationsList', file=filename)
    cleaned = []
    seen = set()
    for relation in relations:
        if not isinstance(relation, dict):
            raise UserError('err.relationEntry', file=filename)
        kind = relation.get('type')
        if kind not in ALL_RELATION_TYPES:
            raise UserError('err.relationType', file=filename, kind=kind)
        if kind == 'include':
            raise UserError('err.relationInclude', file=filename)
        slug = str(relation.get('slug') or '').strip().lower()
        project_id = str(relation.get('projectID') or '').strip()
        if not slug or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,99}', slug):
            raise UserError('err.relationSlug', file=filename)
        if project_id and (not project_id.isdecimal() or int(project_id) <= 0):
            raise UserError('err.relationId', file=filename)
        key = (slug, kind)
        if key in seen:
            continue
        seen.add(key)
        item = {'slug': slug, 'type': kind}
        if project_id:
            item['projectID'] = int(project_id)
        cleaned.append(item)
    return cleaned


def common_checks(data):
    kind = project_type(data)
    release_type = data.get('releaseType', 'release')
    if release_type not in RELEASE_TYPES:
        raise UserError('err.releaseType', file='')
    rows = data.get('entries')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise UserError('err.entries')
    if not isinstance(data.get('changelog', ''), str):
        raise UserError('err.changelog')
    return kind, release_type, rows


def row_changelog(row, data):
    text = row.get('changelog') if row.get('changelogOverride') else data.get('changelog', '')
    return str(text or '')


def validate_cf_job(data, require_token=True):
    kind, release_type, rows = common_checks(data)
    token = saved_token('curseforge', data.get('token', '')) if require_token else ''
    project = str(data.get('projectId', '')).strip()
    if require_token and (not token or not project.isdecimal()):
        raise UserError('err.cfJobBasics')
    if not project.isdecimal():
        raise UserError('err.cfProject')
    stored = stored_files()
    checked = []
    for row in rows:
        item = stored.get(row.get('id')) if isinstance(row, dict) else None
        if not item or not Path(item['path']).exists():
            raise UserError('err.fileGone')
        if 'curseforge' not in platforms_for(kind, item['name']) or row.get('publishCF') is False:
            continue
        version_ids = row.get('versionIds', [])
        if not isinstance(version_ids, list) or not version_ids or any(
                not isinstance(x, int) or isinstance(x, bool) or x <= 0 for x in version_ids):
            raise UserError('err.cfVersions', file=item['name'])
        version_ids = list(dict.fromkeys(version_ids))
        row_release = row.get('releaseType') or release_type
        if row_release not in RELEASE_TYPES:
            raise UserError('err.releaseType', file=item['name'])
        relations = validate_relations(row.get('relations', []), item['name'])
        metadata = {
            'displayName': str(row.get('displayName') or item['name'])[:200],
            'releaseType': row_release,
            'changelog': row_changelog(row, data),
            'changelogType': 'markdown',
            'gameVersions': version_ids,
            'isMarkedForManualRelease': bool(data.get('manualRelease', False)),
        }
        if relations:
            metadata['relations'] = {'projects': relations}
        entry = {'id': row['id'], 'path': item['path'], 'name': item['name'], 'metadata': metadata}
        server_pack = row.get('serverPackId')
        if kind == 'modpack' and server_pack:
            pack = stored.get(server_pack)
            if not pack or not pack['name'].lower().endswith('.zip') or not Path(pack['path']).exists():
                raise UserError('err.serverPack', file=item['name'])
            entry['serverPack'] = {'path': pack['path'], 'name': pack['name'],
                                   'metadata': {'displayName': (metadata['displayName'] + ' Server Pack')[:200],
                                                'releaseType': row_release, 'changelog': metadata['changelog'],
                                                'changelogType': 'markdown', 'parentFileID': None}}
        checked.append(entry)
    if not checked:
        raise UserError('err.noneForPlatform', platform='CurseForge')
    return token, project, checked


def post_cf_file(token, project, path, name, metadata):
    with open(path, 'rb') as stream:
        response = requests.post(
            f'{CF_API}/projects/{project}/upload-file',
            headers={'X-Api-Token': token, 'User-Agent': USER_AGENT},
            data={'metadata': json.dumps(metadata, ensure_ascii=False)},
            files={'file': (name, stream, CONTENT_TYPES.get(Path(name).suffix.lower(), 'application/octet-stream'))},
            timeout=(20, 600),
        )
    if not response.ok:
        raise RuntimeError(f'HTTP {response.status_code}: {response.text[:500]}')
    try:
        result = response.json()
    except ValueError:
        result = {}
    if 'id' not in result:
        raise RuntimeError(t('up.noId', job_lang(), detail=response.text[:250]))
    return result['id']


def job_lang():
    return getattr(threading.current_thread(), 'modferry_lang', 'en')


def set_row(jobid, rowid, state):
    with jobs_lock:
        jobs[jobid]['rows'][rowid] = state


def run_cf_upload(jobid, token, project, entries, context):
    threading.current_thread().modferry_lang = context['lang']
    for row in entries:
        set_row(jobid, row['id'], {'status': 'uploading', 'message': t('up.uploading', context['lang'])})
        try:
            file_id = post_cf_file(token, project, row['path'], row['name'], row['metadata'])
            url = cf_link(context['kind'], project, context['slug'], file_id)
            outcome = {'status': 'success', 'message': t('up.cfDone', context['lang'], id=file_id), 'fileId': file_id, 'url': url}
            if row.get('serverPack'):
                meta = dict(row['serverPack']['metadata'], parentFileID=file_id)
                try:
                    server_id = post_cf_file(token, project, row['serverPack']['path'], row['serverPack']['name'], meta)
                    outcome['message'] = t('up.cfServerPack', context['lang'], id=file_id, sid=server_id)
                    outcome['serverPackId'] = server_id
                except Exception as exc:  # main file stays uploaded; report, never re-upload it
                    outcome['message'] = t('up.cfServerPackFailed', context['lang'], id=file_id, detail=str(exc)[:300])
                    outcome['warning'] = True
            add_history({'time': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'platform': 'curseforge',
                         'project': project, 'projectType': context['kind'], 'file': row['name'],
                         'displayName': row['metadata']['displayName'], 'id': file_id, 'url': url,
                         'releaseType': row['metadata']['releaseType'], 'versions': row.get('versionNames', [])})
        except Exception as exc:
            outcome = {'status': 'error', 'message': str(exc)[:500]}
        set_row(jobid, row['id'], outcome)
    with jobs_lock:
        jobs[jobid]['done'] = True


# ---------------------------------------------------------------- Modrinth upload

# Modrinth v2 Create Version: https://docs.modrinth.com/api/operations/createversion/
MODRINTH_TYPES = {'requiredDependency': 'required', 'optionalDependency': 'optional',
                  'incompatible': 'incompatible', 'embeddedLibrary': 'embedded'}
MODRINTH_ENVIRONMENTS = {'client_and_server', 'client_only', 'client_only_server_optional',
                         'singleplayer_only', 'server_only', 'server_only_client_optional',
                         'dedicated_server_only', 'client_or_server', 'client_or_server_prefers_both'}
MODRINTH_STATUSES = ('listed', 'unlisted', 'draft', 'archived')
# Loader tags per project type (GET /v2/tag/loader, supported_project_types).
MODRINTH_LOADERS = {
    'resourcepack': ('minecraft',),
    'datapack': ('datapack',),
    'shader': ('iris', 'optifine', 'canvas', 'vanilla'),
    'modpack': ('fabric', 'forge', 'neoforge', 'quilt'),
}


def modrinth_dependencies(relations, filename):
    if not isinstance(relations, list) or len(relations) > 100:
        raise UserError('err.mrDepList', file=filename)
    output = []
    seen = set()
    for relation in relations:
        if not isinstance(relation, dict):
            raise UserError('err.mrDepEntry', file=filename)
        kind = relation.get('type')
        if kind not in MODRINTH_TYPES:
            raise UserError('err.mrDepType', file=filename, kind=kind)
        project_id = str(relation.get('modrinthProjectID') or '').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{3,100}', project_id):
            raise UserError('err.mrDepId', file=filename)
        key = (project_id, kind)
        if key not in seen:
            output.append({'project_id': project_id, 'dependency_type': MODRINTH_TYPES[kind]})
            seen.add(key)
    return output


def validate_modrinth_job(data, require_token=True):
    kind, release_type, rows = common_checks(data)
    token = saved_token('modrinth', data.get('modrinthToken', '')) if require_token else ''
    project = str(data.get('modrinthProject') or '').strip()
    valid_project = re.fullmatch(r'[A-Za-z0-9_-]{3,100}', project)
    if require_token and (not token or not valid_project):
        raise UserError('err.mrJobBasics')
    if not valid_project:
        raise UserError('err.mrProject')
    status = data.get('mrStatus') or 'listed'
    if status not in MODRINTH_STATUSES:
        raise UserError('err.mrStatus')
    stored = stored_files()
    checked = []
    numbers = set()
    for row in rows:
        item = stored.get(row.get('id')) if isinstance(row, dict) else None
        if not item or not Path(item['path']).exists():
            raise UserError('err.fileGone')
        if 'modrinth' not in platforms_for(kind, item['name']) or row.get('publishMR') is False:
            continue
        mc = row.get('mrGameVersions', [])
        loaders = row.get('mrLoaders', [])
        if not isinstance(mc, list) or not mc or any(
                not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]{1,40}', x) for x in mc):
            raise UserError('err.mrVersions', file=item['name'])
        allowed = MODRINTH_LOADERS.get(kind)
        if not isinstance(loaders, list) or not loaders or any(
                not isinstance(x, str) or not re.fullmatch(r'[a-z0-9_-]{1,50}', x) for x in loaders) or (
                allowed and any(x not in allowed for x in loaders)):
            raise UserError('err.mrLoaders', file=item['name'], allowed=', '.join(allowed or ('fabric', 'forge', 'neoforge', 'quilt', '…')))
        number = str(row.get('mrVersionNumber') or '').strip()
        if not number or len(number) > 100:
            raise UserError('err.mrNumber', file=item['name'])
        if number in numbers:
            raise UserError('err.mrNumberDup', number=number)
        numbers.add(number)
        row_release = row.get('releaseType') or release_type
        if row_release not in RELEASE_TYPES:
            raise UserError('err.releaseType', file=item['name'])
        meta = {'name': str(row.get('displayName') or item['name'])[:200],
                'version_number': number, 'project_id': project,
                'game_versions': list(dict.fromkeys(mc)), 'loaders': list(dict.fromkeys(loaders)),
                'version_type': row_release, 'changelog': row_changelog(row, data),
                'dependencies': modrinth_dependencies(row.get('relations', []), item['name']),
                'featured': bool(data.get('mrFeatured', False)), 'status': status,
                'file_parts': ['file'], 'primary_file': 'file'}
        if kind in ('mod', 'modpack'):
            env = str(row.get('mrEnvironment') or 'client_and_server')
            if env not in MODRINTH_ENVIRONMENTS:
                raise UserError('err.mrEnv', file=item['name'])
            meta['environment'] = env
        checked.append({'id': row['id'], 'path': item['path'], 'name': item['name'], 'metadata': meta})
    if not checked:
        raise UserError('err.noneForPlatform', platform='Modrinth')
    return token, checked


def has_token(platform, data):
    """True if a token was supplied or is saved (and the store is unlocked). Never returns the token."""
    supplied = data.get('token' if platform == 'curseforge' else 'modrinthToken', '')
    try:
        return bool(saved_token(platform, supplied))
    except (ValueError, OSError):
        return False


def resolve_modrinth_project(token, project):
    res = requests.get(f'{MR_API}/project/{project}', headers={'Authorization': token, 'User-Agent': USER_AGENT}, timeout=20)
    res.raise_for_status()
    return res.json()['id']


def run_modrinth_upload(jobid, token, entries, context):
    headers = {'Authorization': token, 'User-Agent': USER_AGENT}
    for row in entries:
        set_row(jobid, row['id'], {'status': 'uploading', 'message': t('up.uploading', context['lang'])})
        try:
            suffix = Path(row['name']).suffix.lower()
            with open(row['path'], 'rb') as stream:
                result = requests.post(f'{MR_API}/version', headers=headers,
                                       data={'data': json.dumps(row['metadata'], ensure_ascii=False)},
                                       files={'file': (row['name'], stream, CONTENT_TYPES.get(suffix, 'application/octet-stream'))},
                                       timeout=(20, 600))
            if not result.ok:
                raise RuntimeError(f'Modrinth HTTP {result.status_code}: {result.text[:400]}')
            payload = result.json()
            if not payload.get('id'):
                raise RuntimeError(t('up.noId', context['lang'], detail=result.text[:250]))
            url = mr_link(row['metadata']['project_id'], payload['id'])
            outcome = {'status': 'success', 'message': t('up.mrDone', context['lang'], id=payload['id']),
                       'versionId': payload['id'], 'url': url}
            add_history({'time': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'platform': 'modrinth',
                         'project': row['metadata']['project_id'], 'projectType': context['kind'], 'file': row['name'],
                         'displayName': row['metadata']['name'], 'id': payload['id'], 'url': url,
                         'releaseType': row['metadata']['version_type'], 'versions': row['metadata']['game_versions']})
        except Exception as exc:
            outcome = {'status': 'error', 'message': str(exc)[:450]}
        set_row(jobid, row['id'], outcome)
    with jobs_lock:
        jobs[jobid]['done'] = True


# ---------------------------------------------------------------- upload endpoints

def start_job(platform, target, args, entries):
    with jobs_lock:
        if any(not job['done'] for job in jobs.values()):
            return api_error(t('err.busy', lang()), 409)
        jobid = secrets.token_urlsafe(16)
        jobs[jobid] = {'done': False, 'platform': platform,
                       'rows': {r['id']: {'status': 'pending', 'message': t('up.pending', lang())} for r in entries}}
    threading.Thread(target=target, args=(jobid, *args), daemon=True).start()
    return jsonify(jobId=jobid)


@app.post('/api/upload')
def upload():
    data = request.get_json(silent=True) or {}
    platform = data.get('platform', 'curseforge')
    context = {'lang': lang(), 'kind': data.get('projectType', 'mod'), 'slug': str(data.get('cfSlug') or '').strip().lower()}
    try:
        if platform == 'curseforge':
            token, project, entries = validate_cf_job(data)
            names = {r.get('id'): r.get('versionNames', []) for r in data.get('entries', []) if isinstance(r, dict)}
            for entry in entries:
                entry['versionNames'] = [str(x)[:40] for x in names.get(entry['id'], []) if isinstance(x, str)][:50]
            return start_job(platform, run_cf_upload, (token, project, entries, context), entries)
        if platform == 'modrinth':
            token, entries = validate_modrinth_job(data)
            project_cache = {}
            for entry in entries:
                original = entry['metadata']['project_id']
                if original not in project_cache:
                    project_cache[original] = resolve_modrinth_project(token, original)
                entry['metadata']['project_id'] = project_cache[original]
                for dep in entry['metadata']['dependencies']:
                    depid = dep['project_id']
                    if depid not in project_cache:
                        project_cache[depid] = resolve_modrinth_project(token, depid)
                    dep['project_id'] = project_cache[depid]
            return start_job(platform, run_modrinth_upload, (token, entries, context), entries)
        return api_error(t('err.platform', lang()))
    except (ValueError, OSError) as exc:
        return user_error(exc)
    except requests.RequestException as exc:
        return api_error(t('err.mrResolve', lang(), detail=str(exc)), 502)


@app.post('/api/dry-run')
def dry_run():
    """Validate both platforms and return the exact metadata that would be sent, without any network calls."""
    data = request.get_json(silent=True) or {}
    out = {}
    for platform, enabled in (('curseforge', data.get('publishCF', True)), ('modrinth', data.get('publishMR', True))):
        if not enabled:
            continue
        try:
            if platform == 'curseforge':
                _, project, entries = validate_cf_job(data, require_token=False)
                items = []
                for e in entries:
                    item = {'file': e['name'], 'endpoint': f'POST {CF_API}/projects/{project}/upload-file', 'metadata': e['metadata']}
                    if e.get('serverPack'):
                        item['serverPack'] = {'file': e['serverPack']['name'],
                                              'metadata': dict(e['serverPack']['metadata'], parentFileID='<id of main file>')}
                    items.append(item)
            else:
                _, entries = validate_modrinth_job(data, require_token=False)
                items = [{'file': e['name'], 'endpoint': f'POST {MR_API}/version', 'metadata': e['metadata']} for e in entries]
            out[platform] = {'ok': True, 'items': items, 'hasToken': has_token(platform, data)}
        except ValueError as exc:
            out[platform] = {'ok': False, 'error': exc.text(lang()) if isinstance(exc, UserError) else str(exc)}
    return jsonify(out)


@app.get('/api/upload/<jobid>')
def upload_status(jobid):
    with jobs_lock:
        if jobid not in jobs:
            return api_error(t('err.unknownJob', lang()), 404)
        return jsonify(jobs[jobid])


def main():
    removed = clean_cache()
    if removed:
        print(f'ModFerry: {removed} cached file(s) from a previous session removed.')
    print(f'ModFerry {VERSION}: http://{APP_HOST}:{APP_PORT}')
    app.run(host=APP_HOST, port=APP_PORT, debug=False, threaded=True)


if __name__ == '__main__':
    main()
