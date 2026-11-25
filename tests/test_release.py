"""Version handling and release packaging. Runs without network access."""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from version import RELEASE_PATTERN, read_version  # noqa: E402
import make_release  # noqa: E402


class VersionTest(unittest.TestCase):
    def test_version_file_wins(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'VERSION').write_text('5.1.0\n', 'utf-8')
            self.assertEqual(read_version(d), '5.1.0')

    def test_without_file_or_git(self):
        with tempfile.TemporaryDirectory() as d:
            # A fresh temp folder is no Git repository, so the fallback applies.
            self.assertEqual(read_version(d), 'dev')

    def test_release_pattern(self):
        for ok in ('5.1.0', '10.0.12', '5.1.0-beta.1', '5.1.0+build.7'):
            self.assertTrue(RELEASE_PATTERN.fullmatch(ok), ok)
        for bad in ('v5.1.0', '5.1', 'latest', '5.1.0 beta', '5.1.0/../x'):
            self.assertFalse(RELEASE_PATTERN.fullmatch(bad), bad)


class ReleaseZipTest(unittest.TestCase):
    def test_zip_contains_version_and_no_user_data(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(make_release.main(['--version', '9.8.7', '--out', d]), 0)
            archive = Path(d) / 'ModFerry-9.8.7.zip'
            with zipfile.ZipFile(archive) as z:
                names = z.namelist()
                self.assertEqual(z.read('ModFerry/VERSION').decode().strip(), '9.8.7')
            self.assertIn('ModFerry/app.py', names)
            self.assertIn('ModFerry/version.py', names)
            self.assertFalse([n for n in names if '/data/' in n or '.venv' in n or 'tokens' in n])

    def test_invalid_version_rejected(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(SystemExit):
            make_release.main(['--version', 'v1.0', '--out', d])


if __name__ == '__main__':
    unittest.main()
