"""Build the release ZIP: python tools/make_release.py  ->  dist/ModFerry-<version>.zip

Only files that belong to the program are packed; user data, venv and caches never are.
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ['app.py', 'file_inspect.py', 'jar_inspect.py', 'pack_formats.py', 'secrets_store.py',
           'markdown_preview.py', 'messages.py', 'requirements.txt', 'start-windows.bat', 'start-linux.sh',
           'README.md', 'CHANGELOG.md', 'LICENSE', 'static', 'docs']
SKIP_PARTS = {'__pycache__', '.venv', 'data', '.git'}


def main():
    version = re.search(r"^VERSION = '([^']+)'", (ROOT / 'app.py').read_text('utf-8'), re.M).group(1)
    out = ROOT / 'dist' / f'ModFerry-{version}.zip'
    out.parent.mkdir(exist_ok=True)
    count = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as archive:
        for entry in INCLUDE:
            path = ROOT / entry
            files = [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file())
            for file in files:
                rel = file.relative_to(ROOT)
                if SKIP_PARTS & set(rel.parts) or file.suffix == '.pyc':
                    continue
                info = zipfile.ZipInfo.from_file(file, f'ModFerry/{rel.as_posix()}')
                if file.suffix == '.sh':
                    info.external_attr = 0o100755 << 16  # keep the launcher executable on Linux/macOS
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, file.read_bytes())
                count += 1
    print(f'{out} ({count} files)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
