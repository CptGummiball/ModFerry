"""Metadata detection (mods, packs, modpacks) and token encryption. Runs without network access."""
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jar_inspect import inspect_jar, exact_mc_version, filename_hint  # noqa: E402
from secrets_store import TokenStore  # noqa: E402
from pack_formats import inspect_pack  # noqa: E402
from file_inspect import inspect_upload, version_from_filename  # noqa: E402


def make_zip(path, entries):
    with zipfile.ZipFile(path, 'w') as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return path


class MetadataTest(unittest.TestCase):
    def test_26_2_over_mod_version(self):
        self.assertEqual(filename_hint('mymod-1.1.2-neoforge-26.2.jar')['minecraft'], ['26.2'])
        self.assertEqual(filename_hint('mymod-1.1.2-neoforge-26.3.jar')['minecraft'], ['26.3'])

    def test_ranges_never_guessed(self):
        self.assertIsNone(exact_mc_version('[26.2,26.3)'))
        self.assertIsNone(exact_mc_version('[26.2,)'))
        self.assertEqual(exact_mc_version('[26.2]'), '26.2')

    def test_fabric_json(self):
        with tempfile.TemporaryDirectory() as d:
            jar = make_zip(Path(d) / 'mymod-1.1.2.jar', {
                'fabric.mod.json': json.dumps({'depends': {'minecraft': '26.2'}}),
                'test/Test.class': b'\xca\xfe\xba\xbe\x00\x00\x00\x41'})
            actual = inspect_jar(jar, jar.name)
            self.assertEqual(actual['minecraft'], ['26.2'])
            self.assertEqual(actual['loaders'], ['fabric'])
            self.assertEqual(actual['java'], ['21'])

    def test_neoforge_toml(self):
        with tempfile.TemporaryDirectory() as d:
            jar = make_zip(Path(d) / 'mymod-1.1.2.jar', {
                'META-INF/neoforge.mods.toml': '[[dependencies.mymod]]\nmodId="minecraft"\nversionRange="[26.3]"\n'})
            actual = inspect_jar(jar, jar.name)
            self.assertEqual(actual['minecraft'], ['26.3'])
            self.assertEqual(actual['loaders'], ['neoforge'])


class ModVersionTest(unittest.TestCase):
    def test_fabric_version(self):
        with tempfile.TemporaryDirectory() as d:
            jar = make_zip(Path(d) / 'x.jar', {
                'fabric.mod.json': json.dumps({'version': '1.4.2+mc1.21.1', 'depends': {'minecraft': '1.21.1'}})})
            self.assertEqual(inspect_jar(jar, jar.name)['modVersion'], '1.4.2+mc1.21.1')

    def test_toml_placeholder_uses_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            jar = make_zip(Path(d) / 'x.jar', {
                'META-INF/neoforge.mods.toml': '[[mods]]\nmodId="x"\nversion="${file.jarVersion}"\n',
                'META-INF/MANIFEST.MF': 'Manifest-Version: 1.0\r\nImplementation-Version: 2.0.1\r\n'})
            self.assertEqual(inspect_jar(jar, jar.name)['modVersion'], '2.0.1')

    def test_version_from_filename_skips_minecraft(self):
        self.assertEqual(version_from_filename('pack-1.21.1-2.3.0.zip', ['1.21.1']), '2.3.0')
        self.assertEqual(version_from_filename('pack-1.21.1.zip', ['1.21.1']), '')


class PackFormatTest(unittest.TestCase):
    def pack(self, meta, kind):
        with tempfile.TemporaryDirectory() as d:
            path = make_zip(Path(d) / 'pack.zip', {'pack.mcmeta': json.dumps({'pack': meta}), 'assets/a': '', 'data/a': ''})
            return inspect_pack(path, path.name, kind)

    def test_pack_format_int(self):
        self.assertEqual(self.pack({'pack_format': 34}, 'resourcepack')['minecraft'], ['1.21', '1.21.1'])
        self.assertEqual(self.pack({'pack_format': 48}, 'datapack')['minecraft'], ['1.21', '1.21.1'])

    def test_supported_formats_range(self):
        result = self.pack({'pack_format': 34, 'supported_formats': [34, 46]}, 'resourcepack')
        self.assertEqual(result['minecraft'], ['1.21', '1.21.1', '1.21.2', '1.21.3', '1.21.4'])

    def test_min_max_format_with_minor(self):
        self.assertEqual(self.pack({'min_format': 94, 'max_format': 94}, 'datapack')['minecraft'], ['1.21.11'])
        self.assertEqual(self.pack({'min_format': [101, 1], 'max_format': [107, 1]}, 'datapack')['minecraft'],
                         ['26.1', '26.1.1', '26.1.2', '26.2'])

    def test_unknown_future_format(self):
        result = self.pack({'min_format': 500, 'max_format': 500}, 'resourcepack')
        self.assertEqual(result['minecraft'], [])
        self.assertEqual(result['warning'], 'warn.unknownPackFormat')


class ModpackTest(unittest.TestCase):
    def test_curseforge_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            path = make_zip(Path(d) / 'pack-2.1.zip', {'manifest.json': json.dumps({
                'minecraft': {'version': '1.21.1', 'modLoaders': [{'id': 'neoforge-21.1.1', 'primary': True}]}, 'version': '2.1'})})
            r = inspect_upload(path, path.name, 'modpack')
            self.assertEqual((r['minecraft'], r['loaders'], r['modVersion'], r['platforms']),
                             (['1.21.1'], ['neoforge'], '2.1', ['curseforge']))

    def test_mrpack_index(self):
        with tempfile.TemporaryDirectory() as d:
            path = make_zip(Path(d) / 'pack.mrpack', {'modrinth.index.json': json.dumps({
                'formatVersion': 1, 'game': 'minecraft', 'versionId': '3.0',
                'dependencies': {'minecraft': '26.2', 'fabric-loader': '0.17.0'}})})
            r = inspect_upload(path, path.name, 'modpack')
            self.assertEqual((r['minecraft'], r['loaders'], r['modVersion'], r['platforms']),
                             (['26.2'], ['fabric'], '3.0', ['modrinth']))


class TokenTest(unittest.TestCase):
    def test_encryption_without_plaintext(self):
        with tempfile.TemporaryDirectory() as d:
            store = TokenStore(d)
            if store.mode == 'passphrase':
                store.unlock('a-very-long-test-master-password')
            store.write({'curseforge': 'VERY_SECRET_CF', 'modrinth': 'VERY_SECRET_MR'})
            raw = store.path.read_text()
            self.assertNotIn('VERY_SECRET_CF', raw)
            self.assertEqual(store.read()['modrinth'], 'VERY_SECRET_MR')
            store2 = TokenStore(d)
            if store.mode == 'passphrase':
                with self.assertRaises(ValueError):
                    store2.unlock('incorrect-password12345')
                store2.unlock('a-very-long-test-master-password')
            self.assertEqual(store2.read()['curseforge'], 'VERY_SECRET_CF')


if __name__ == '__main__':
    unittest.main()
