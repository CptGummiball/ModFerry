"""Minecraft Java release versions -> resource/data pack formats.

Source: https://minecraft.wiki/w/Pack_format (release tables, read 2026-11-25).
Formats since 1.21.9 have a minor part (e.g. 88.0). Only release versions are listed;
a pack whose declared formats are newer than this table yields no suggestion and must
be assigned manually. Extend ``TABLE`` when Mojang releases a new version.
"""
import json
import math
import zipfile

# (minecraft versions, resource pack format, data pack format)
TABLE = [
    (('1.13', '1.13.1', '1.13.2', '1.14', '1.14.1', '1.14.2', '1.14.3', '1.14.4'), (4, 0), (4, 0)),
    (('1.15', '1.15.1', '1.15.2', '1.16', '1.16.1'), (5, 0), (5, 0)),
    (('1.16.2', '1.16.3', '1.16.4', '1.16.5'), (6, 0), (6, 0)),
    (('1.17', '1.17.1'), (7, 0), (7, 0)),
    (('1.18', '1.18.1'), (8, 0), (8, 0)),
    (('1.18.2',), (8, 0), (9, 0)),
    (('1.19', '1.19.1', '1.19.2'), (9, 0), (10, 0)),
    (('1.19.3',), (12, 0), (10, 0)),
    (('1.19.4',), (13, 0), (12, 0)),
    (('1.20', '1.20.1'), (15, 0), (15, 0)),
    (('1.20.2',), (18, 0), (18, 0)),
    (('1.20.3', '1.20.4'), (22, 0), (26, 0)),
    (('1.20.5', '1.20.6'), (32, 0), (41, 0)),
    (('1.21', '1.21.1'), (34, 0), (48, 0)),
    (('1.21.2', '1.21.3'), (42, 0), (57, 0)),
    (('1.21.4',), (46, 0), (61, 0)),
    (('1.21.5',), (55, 0), (71, 0)),
    (('1.21.6',), (63, 0), (80, 0)),
    (('1.21.7', '1.21.8'), (64, 0), (81, 0)),
    (('1.21.9', '1.21.10'), (69, 0), (88, 0)),
    (('1.21.11',), (75, 0), (94, 1)),
    (('26.1', '26.1.1', '26.1.2'), (84, 0), (101, 1)),
    (('26.2',), (88, 0), (107, 1)),
    (('26.3',), (97, 1), (121, 0)),
]

INF = math.inf


def _fmt(value, upper=False):
    """Parse an int / float / [major, minor] format. A bare int as upper bound means any minor."""
    if isinstance(value, bool):
        raise ValueError
    if isinstance(value, int):
        return (value, INF if upper else 0)
    if isinstance(value, float):
        major, _, minor = repr(value).partition('.')
        return (int(major), int(minor or 0))
    if isinstance(value, list) and len(value) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in value):
        return (value[0], value[1])
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], int):
        return (value[0], INF if upper else 0)
    raise ValueError


def declared_range(pack):
    """Return the (min, max) format tuple declared in the ``pack`` object of pack.mcmeta."""
    if not isinstance(pack, dict):
        return None
    if 'min_format' in pack and 'max_format' in pack:
        return _fmt(pack['min_format']), _fmt(pack['max_format'], True)
    supported = pack.get('supported_formats')
    if supported is not None:
        if isinstance(supported, int) and not isinstance(supported, bool):
            return (supported, 0), (supported, INF)
        if isinstance(supported, list) and len(supported) == 2:
            return (supported[0], 0), (supported[1], INF)
        if isinstance(supported, dict) and 'min_inclusive' in supported and 'max_inclusive' in supported:
            return (supported['min_inclusive'], 0), (supported['max_inclusive'], INF)
    if 'pack_format' in pack:
        low = _fmt(pack['pack_format'])
        return low, (low[0], INF)
    return None


def versions_for(kind, low, high):
    """Minecraft release versions whose pack format lies in [low, high]."""
    index = 1 if kind == 'resourcepack' else 2
    out = []
    for versions, *formats in TABLE:
        fmt = formats[index - 1]
        if low <= fmt <= high:
            out.extend(versions)
    return out


def inspect_pack(path, filename, kind):
    """Read pack.mcmeta from a resource/data pack zip and suggest Minecraft versions."""
    result = {'minecraft': [], 'loaders': [], 'java': [], 'source': 'filename', 'warning': '', 'evidence': [], 'modVersion': ''}
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if 'pack.mcmeta' not in names:
                if kind in ('resourcepack', 'datapack'):
                    result['warning'] = 'warn.noMcmeta'
                return result
            info = archive.getinfo('pack.mcmeta')
            if info.file_size > 256000:
                raise ValueError('pack.mcmeta too large')
            meta = json.loads(archive.read('pack.mcmeta').decode('utf-8-sig'))
            if kind == 'datapack' and not any(n.startswith('data/') for n in names):
                result['warning'] = 'warn.noDataFolder'
            if kind == 'resourcepack' and not any(n.startswith('assets/') for n in names):
                result['warning'] = 'warn.noAssetsFolder'
    except (zipfile.BadZipFile, ValueError, UnicodeError, KeyError, OSError) as exc:
        result['warning'] = 'warn.unreadable:' + str(exc)[:150]
        return result
    try:
        bounds = declared_range(meta.get('pack'))
    except (ValueError, TypeError):
        bounds = None
    if not bounds:
        result['warning'] = result['warning'] or 'warn.noPackFormat'
        return result
    low, high = bounds
    result['evidence'].append('pack.mcmeta format %s to %s' % (_show(low), _show(high)))
    found = versions_for(kind, low, high)
    if found:
        result['minecraft'] = found
        result['source'] = 'pack.mcmeta'
    else:
        result['warning'] = 'warn.unknownPackFormat'
    return result


def _show(fmt):
    major, minor = fmt
    return str(major) if minor in (0, INF) else '%d.%d' % (major, minor)
