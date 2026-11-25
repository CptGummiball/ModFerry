"""Dispatch metadata detection by project type. Never guesses beyond what the file declares."""
import json
import re
import zipfile
from pathlib import Path

from jar_inspect import inspect_jar, filename_hint, MC_VERSION
from pack_formats import inspect_pack

PROJECT_TYPES = ('mod', 'resourcepack', 'datapack', 'shader', 'modpack')

# Allowed file extensions per project type and which platforms accept them.
EXTENSIONS = {
    'mod': {'.jar': ('curseforge', 'modrinth')},
    'resourcepack': {'.zip': ('curseforge', 'modrinth')},
    'datapack': {'.zip': ('curseforge', 'modrinth')},
    'shader': {'.zip': ('curseforge', 'modrinth')},
    # CurseForge and Modrinth use different modpack formats, so each file goes to one platform.
    'modpack': {'.zip': ('curseforge',), '.mrpack': ('modrinth',)},
}

MODRINTH_LOADER_KEYS = {'fabric-loader': 'fabric', 'quilt-loader': 'quilt', 'forge': 'forge', 'neoforge': 'neoforge'}


def platforms_for(kind, filename):
    return EXTENSIONS.get(kind, {}).get(Path(filename).suffix.lower(), ())


def version_from_filename(filename, minecraft=()):
    """Semantic version in the file name that is not one of the Minecraft versions."""
    stem = Path(filename).stem
    for match in re.finditer(r'(?:^|[-_ ])v?(\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z][A-Za-z0-9.]*)?)(?=$|[-_ ])', stem):
        value = match.group(1)
        if value not in minecraft and not MC_VERSION.fullmatch(value):
            return value
    return ''


def inspect_modpack(path, filename):
    result = {'minecraft': [], 'loaders': [], 'java': [], 'source': 'filename', 'warning': '', 'evidence': [], 'modVersion': ''}
    suffix = Path(filename).suffix.lower()
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if suffix == '.mrpack':
                if 'modrinth.index.json' not in names:
                    result['warning'] = 'warn.noMrIndex'
                    return result
                index = json.loads(archive.read('modrinth.index.json').decode('utf-8-sig'))
                deps = index.get('dependencies') or {}
                if isinstance(deps.get('minecraft'), str):
                    result['minecraft'] = [deps['minecraft']]
                result['loaders'] = [MODRINTH_LOADER_KEYS[k] for k in deps if k in MODRINTH_LOADER_KEYS][:1]
                result['modVersion'] = str(index.get('versionId') or '')[:100]
                result['evidence'].append('modrinth.index.json')
                result['source'] = 'modrinth.index.json'
            else:
                if 'manifest.json' not in names:
                    result['warning'] = 'warn.noCfManifest'
                    return result
                manifest = json.loads(archive.read('manifest.json').decode('utf-8-sig'))
                mc = manifest.get('minecraft') or {}
                if isinstance(mc.get('version'), str):
                    result['minecraft'] = [mc['version']]
                for loader in mc.get('modLoaders') or []:
                    ident = str(loader.get('id', '')) if isinstance(loader, dict) else ''
                    name = ident.split('-', 1)[0].lower()
                    if name in ('forge', 'neoforge', 'fabric', 'quilt'):
                        if loader.get('primary') or not result['loaders']:
                            result['loaders'] = [name]
                result['modVersion'] = str(manifest.get('version') or '')[:100]
                result['evidence'].append('manifest.json')
                result['source'] = 'manifest.json'
    except (zipfile.BadZipFile, ValueError, UnicodeError, KeyError, OSError, AttributeError) as exc:
        result['warning'] = 'warn.unreadable:' + str(exc)[:150]
    return result


def inspect_upload(path, filename, kind):
    if kind == 'mod':
        result = inspect_jar(path, filename)
    elif kind == 'modpack':
        result = inspect_modpack(path, filename)
    elif kind in ('resourcepack', 'datapack'):
        result = inspect_pack(path, filename, kind)
    else:  # shader packs carry no reliable version metadata
        result = {'minecraft': [], 'loaders': [], 'java': [], 'source': 'filename', 'warning': '', 'evidence': [], 'modVersion': ''}
    if not result['minecraft'] and kind != 'mod':
        hint = filename_hint(filename)
        result['minecraft'] = hint['minecraft']
        if hint['minecraft']:
            result['source'] = 'filename'
    if not result.get('modVersion'):
        result['modVersion'] = version_from_filename(filename, result['minecraft'])
    result['platforms'] = list(platforms_for(kind, filename))
    return result
