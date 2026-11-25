"""Conservative metadata hints; ambiguous ranges are never interpreted as exact MC releases."""
import json
import re
import zipfile
from pathlib import Path
try:
    import tomllib
except ImportError:
    import tomli as tomllib

# Minecraft 26.x uses a distinct two-part scheme; never infer MC from mod version.
MC_VERSION = re.compile(r'(?<![0-9A-Za-z])(?:1\.(?:[0-9]|[12][0-9])(?:\.[0-9]+)?|2[6-9]\.[0-9]+(?:\.[0-9]+)?)(?![0-9A-Za-z])')
LOADERS = ('neoforge', 'fabric', 'quilt', 'forge')


def exact_mc_version(text):
    """Accept only an unambiguous exact version, not ranges or interpolation."""
    if not isinstance(text, str):
        return None
    s = text.strip()
    if s.startswith('='):
        s = s[1:].strip()
    if s.startswith('[') and s.endswith(']') and ',' not in s:
        s = s[1:-1].strip()
    return s if MC_VERSION.fullmatch(s) else None


def filename_hint(filename):
    stem = Path(filename).stem.lower()
    loaders = [x for x in LOADERS if re.search(r'(?<![a-z])'+x+r'(?![a-z])', stem)]
    if 'neoforge' in loaders and 'forge' in loaders:
        loaders.remove('forge')
    # Not a blanket 1.2.3 match: if multiple valid versions are present, flag ambiguity.
    matches = list(dict.fromkeys(MC_VERSION.findall(stem)))
    modern = [m for m in matches if re.fullmatch(r'2[6-9]\.\d+(?:\.\d+)?',m)]
    # Prefer the new 26.x Minecraft numbering over a separately present 1.x mod version.
    chosen = modern if len(modern)==1 else matches
    return {'minecraft': chosen if len(chosen) == 1 else [], 'loaders': loaders[:1],
            'warning': 'warn.multipleMcInName' if len(chosen)>1 else ''}


def inspect_jar(path, filename):
    result = {'minecraft': [], 'loaders': [], 'java': [], 'source': 'filename', 'warning': '', 'evidence': [], 'modVersion': ''}
    fallback = filename_hint(filename)
    result.update({k: fallback[k] for k in ('minecraft', 'loaders', 'warning')})
    mc_hints, loaders, evidence, mod_versions = [], [], [], []
    try:
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > 50000:
                raise ValueError('JAR hat zu viele Einträge')
            names = set(archive.namelist())
            def read(name, maxsize=256000):
                if name not in names or archive.getinfo(name).file_size > maxsize:
                    return None
                return archive.read(name)
            if 'fabric.mod.json' in names:
                raw = read('fabric.mod.json')
                if raw:
                    obj = json.loads(raw)
                    loaders.append('fabric')
                    if isinstance(obj.get('version'), str): mod_versions.append(obj['version'])
                    val = obj.get('depends', {}).get('minecraft')
                    hint = exact_mc_version(val)
                    if hint: mc_hints.append(hint)
                    evidence.append('fabric.mod.json' + (f' minecraft={val}' if val else ''))
            if 'quilt.mod.json' in names:
                raw = read('quilt.mod.json')
                if raw:
                    obj = json.loads(raw)
                    loaders.append('quilt')
                    qv = obj.get('quilt_loader', {}).get('version')
                    if isinstance(qv, str): mod_versions.append(qv)
                    # Quilt depends entries usually contain version ranges, intentionally not guessed.
                    depends = obj.get('quilt_loader', {}).get('depends', [])
                    for dep in depends if isinstance(depends,list) else []:
                        if isinstance(dep,dict) and dep.get('id')=='minecraft':
                            hint = exact_mc_version(dep.get('versions'))
                            if hint: mc_hints.append(hint)
                    evidence.append('quilt.mod.json')
            for name, loader in (('META-INF/neoforge.mods.toml','neoforge'),('META-INF/mods.toml','forge')):
                raw = read(name)
                if raw:
                    loaders.append(loader)
                    data = tomllib.loads(raw.decode('utf-8-sig'))
                    for mod in data.get('mods', []) if isinstance(data.get('mods'), list) else []:
                        if isinstance(mod, dict) and isinstance(mod.get('version'), str):
                            mod_versions.append(mod['version'])
                            break
                    for groups in data.get('dependencies', {}).values():
                        if not isinstance(groups, list): continue
                        for dep in groups:
                            if isinstance(dep, dict) and str(dep.get('modId','')).lower()=='minecraft':
                                val=dep.get('versionRange')
                                hint=exact_mc_version(val)
                                if hint: mc_hints.append(hint)
                    evidence.append(name)
            majors=[]
            for name in names:
                if name.endswith('.class') and not name.startswith('META-INF/versions/'):
                    info=archive.getinfo(name)
                    if info.file_size>0:
                        with archive.open(name) as source:
                            header=source.read(8)
                        if len(header)==8 and header[:4]==b'\xca\xfe\xba\xbe':
                            major=int.from_bytes(header[6:8],'big')
                            if 45<=major<=75: majors.append(major-44)
            if majors: result['java']=[str(max(majors))]
            if any('${' in v for v in mod_versions):
                manifest = read('META-INF/MANIFEST.MF')
                found = re.search(rb'^Implementation-Version:\s*(\S+)', manifest or b'', re.M)
                mod_versions = [found.group(1).decode('utf-8', 'replace')] if found else []
    except (ValueError, zipfile.BadZipFile, json.JSONDecodeError, UnicodeError, KeyError) as exc:
        result['warning'] = ('warn.unreadable:'+str(exc))[:250]
    mc_hints = list(dict.fromkeys(mc_hints))
    if len(mc_hints)==1:
        result['minecraft']=mc_hints
        result['source']='jar-metadata'
    elif len(mc_hints)>1:
        result['minecraft']=[]
        result['warning']='warn.conflictingMc'
    if loaders:
        result['loaders']=list(dict.fromkeys(loaders))[:1]
    result['evidence']=evidence
    clean = [v for v in mod_versions if v and '${' not in v and len(v) <= 100]
    result['modVersion'] = clean[0] if clean else ''
    return result
