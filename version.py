"""Where ModFerry's version number comes from.

1. Release ZIPs contain a ``VERSION`` file, written by ``tools/make_release.py`` from the Git tag.
2. A Git checkout asks ``git describe`` (e.g. ``5.0.0`` on a tag, ``5.0.0-3-gabc1234`` after it).
3. Otherwise the version is ``dev``.

Nobody has to bump a version number in the code by hand.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Accepted release versions: 5.1.0, 5.1.0-beta.1, 5.1.0+build.7
RELEASE_PATTERN = re.compile(r'\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.]+)?')


def read_version(root=ROOT):
    version_file = Path(root) / 'VERSION'
    if version_file.is_file():
        value = version_file.read_text('utf-8').strip()
        if value:
            return value
    try:
        result = subprocess.run(['git', 'describe', '--tags', '--always', '--dirty'], cwd=root,
                                capture_output=True, text=True, timeout=5)
        described = result.stdout.strip()
        if result.returncode == 0 and described:
            return described[1:] if described.startswith('v') else described
    except (OSError, subprocess.SubprocessError):
        pass
    return 'dev'


VERSION = read_version()
