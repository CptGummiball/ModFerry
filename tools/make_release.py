"""Build the release ZIP.

    python tools/make_release.py                  version from git describe (or "dev")
    python tools/make_release.py --version 5.1.0  used by the release workflow with the Git tag

Writes dist/ModFerry-<version>.zip. Only files that belong to the program are packed;
user data, venv and caches never are. The version is stored in a VERSION file inside the ZIP.
"""
import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from version import RELEASE_PATTERN, read_version  # noqa: E402

INCLUDE = ['app.py', 'version.py', 'file_inspect.py', 'jar_inspect.py', 'pack_formats.py', 'secrets_store.py',
           'markdown_preview.py', 'messages.py', 'requirements.txt', 'start-windows.bat', 'start-linux.sh',
           'README.md', 'CHANGELOG.md', 'LICENSE', 'static', 'docs']
SKIP_PARTS = {'__pycache__', '.venv', 'data', '.git'}


def build(version, out_dir):
    out = Path(out_dir) / f'ModFerry-{version}.zip'
    out.parent.mkdir(parents=True, exist_ok=True)
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
        archive.writestr('ModFerry/VERSION', version + '\n')
    return out, count + 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', help='release version without the leading "v", e.g. 5.1.0')
    parser.add_argument('--out', default=str(ROOT / 'dist'), help='output folder (default: dist)')
    args = parser.parse_args(argv)
    version = args.version or read_version()
    if args.version and not RELEASE_PATTERN.fullmatch(version):
        parser.error(f'"{version}" is not a valid release version (expected e.g. 5.1.0 or 5.1.0-beta.1)')
    out, count = build(version, args.out)
    print(f'{out} ({count} files)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
