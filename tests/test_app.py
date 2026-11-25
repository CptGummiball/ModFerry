import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

# Never touch the real data folder (tokens, profiles, cache) from tests.
_TMP = tempfile.mkdtemp(prefix='modferry-test-')
os.environ['MODFERRY_DATA'] = _TMP
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as module  # noqa: E402


def zip_bytes(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buf.getvalue()


class Client(unittest.TestCase):
    def setUp(self):
        self.client = module.app.test_client()

    def add(self, name, content, kind='mod', **extra):
        data = {'files': (io.BytesIO(content), name), 'projectType': kind, **extra}
        return self.client.post('/api/files', data=data, content_type='multipart/form-data')


class AppTest(Client):
    def test_home(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_info(self):
        info = self.client.get('/api/info').json
        self.assertEqual(info['version'], module.VERSION)
        self.assertIn('modpack', info['projectTypes'])

    def test_foreign_host_rejected(self):
        self.assertEqual(self.client.get('/api/info', headers={'Host': 'evil.example'}).status_code, 403)

    def test_foreign_origin_rejected(self):
        response = self.client.post('/api/profiles', json={'name': 'x'}, headers={'Origin': 'https://evil.example'})
        self.assertEqual(response.status_code, 403)

    def test_upload_rejects_invalid_project(self):
        response = self.client.post('/api/upload', json={'token': 'example', 'projectId': 'bad', 'entries': [{}]})
        self.assertEqual(response.status_code, 400)

    def test_language_header(self):
        de = self.client.post('/api/upload', json={'entries': []}, headers={'X-ModFerry-Lang': 'de'}).json['error']
        en = self.client.post('/api/upload', json={'entries': []}, headers={'X-ModFerry-Lang': 'en'}).json['error']
        self.assertIn('Dateien', de)
        self.assertIn('files', en)

    def test_jar_file_add_and_remove(self):
        response = self.add('test.jar', b'PKfake')
        self.assertEqual(response.status_code, 200)
        fileid = response.json['files'][0]['id']
        self.assertEqual(response.json['files'][0]['detected']['platforms'], ['curseforge', 'modrinth'])
        self.assertEqual(self.client.delete('/api/files/' + fileid).status_code, 200)

    def test_extension_per_project_type(self):
        self.assertEqual(self.add('pack.zip', b'PK', kind='mod').status_code, 400)
        self.assertEqual(self.add('mod.jar', b'PK', kind='resourcepack').status_code, 400)
        response = self.add('pack.mrpack', zip_bytes({'modrinth.index.json': '{}'}), kind='modpack')
        self.assertEqual(response.json['files'][0]['detected']['platforms'], ['modrinth'])

    def test_classification(self):
        self.assertEqual(module.classify({'name': 'NeoForge', 'typeId': 10}, {}), 'loader')
        self.assertEqual(module.classify({'name': 'Java 21', 'typeId': 10}, {}), 'java')
        self.assertEqual(module.classify({'name': 'Server', 'typeId': 10}, {}), 'environment')
        self.assertEqual(module.classify({'name': '1.21.1', 'typeId': 10}, {}), 'other')
        self.assertEqual(module.classify({'name': '26.2', 'typeId': 10}, {10: {'slug': 'minecraft', 'name': 'Minecraft'}}), 'minecraft')

    def test_clean_cache(self):
        (module.FILES / 'orphan.jar').write_bytes(b'x')
        self.assertGreaterEqual(module.clean_cache(), 1)
        self.assertFalse((module.FILES / 'orphan.jar').exists())

    def test_profile_roundtrip_drops_tokens(self):
        self.client.post('/api/profiles', json={'name': 'P', 'settings': {'projectType': 'datapack', 'token': 'SECRET'}})
        profile = self.client.get('/api/profiles').json['profiles']['P']
        self.assertEqual(profile, {'projectType': 'datapack'})
        self.client.delete('/api/profiles/P')
        self.assertNotIn('P', self.client.get('/api/profiles').json['profiles'])

    def test_history(self):
        module.add_history({'platform': 'modrinth', 'id': 'abc'})
        self.assertEqual(self.client.get('/api/history').json['history'][0]['id'], 'abc')
        self.client.delete('/api/history')
        self.assertEqual(self.client.get('/api/history').json['history'], [])


class DryRunTests(Client):
    def test_dry_run_both_platforms(self):
        fileid = self.add('mymod-1.2.0-fabric-1.21.1.jar', b'PKfake').json['files'][0]['id']
        body = {'projectType': 'mod', 'projectId': '123', 'modrinthProject': 'my-mod', 'changelog': 'Hi',
                'mrStatus': 'draft', 'mrFeatured': True,
                'entries': [{'id': fileid, 'versionIds': [9990], 'mrGameVersions': ['1.21.1'], 'mrLoaders': ['fabric'],
                             'mrVersionNumber': '1.2.0+fabric-1.21.1', 'releaseType': 'beta'}]}
        out = self.client.post('/api/dry-run', json=body).json
        self.assertTrue(out['curseforge']['ok'], out)
        self.assertEqual(out['curseforge']['items'][0]['metadata']['gameVersions'], [9990])
        self.assertEqual(out['curseforge']['items'][0]['metadata']['releaseType'], 'beta')
        mr = out['modrinth']['items'][0]['metadata']
        self.assertEqual((mr['status'], mr['featured'], mr['environment']), ('draft', True, 'client_and_server'))

    def test_dry_run_reports_errors(self):
        out = self.client.post('/api/dry-run', json={'projectId': '1', 'modrinthProject': 'abc', 'entries': [{'id': 'nope'}]}).json
        self.assertFalse(out['curseforge']['ok'])
        self.assertFalse(out['modrinth']['ok'])

    def test_resourcepack_modrinth_loader_enforced(self):
        fileid = self.add('pack.zip', zip_bytes({'pack.mcmeta': '{"pack":{"pack_format":34}}', 'assets/x': ''}), kind='resourcepack').json['files'][0]['id']
        body = {'projectType': 'resourcepack', 'modrinthProject': 'my-pack', 'publishCF': False,
                'entries': [{'id': fileid, 'mrGameVersions': ['1.21'], 'mrLoaders': ['fabric'], 'mrVersionNumber': '1'}]}
        self.assertFalse(self.client.post('/api/dry-run', json=body).json['modrinth']['ok'])
        body['entries'][0]['mrLoaders'] = ['minecraft']
        out = self.client.post('/api/dry-run', json=body).json['modrinth']
        self.assertTrue(out['ok'], out)
        self.assertNotIn('environment', out['items'][0]['metadata'])

    def test_modpack_files_split_by_platform(self):
        cf = self.add('pack-1.0.zip', zip_bytes({'manifest.json': '{}'}), kind='modpack').json['files'][0]['id']
        mr = self.add('pack-1.0.mrpack', zip_bytes({'modrinth.index.json': '{}'}), kind='modpack').json['files'][0]['id']
        server = self.add('server.zip', b'PKserver', kind='modpack', purpose='serverpack').json['files'][0]['id']
        body = {'projectType': 'modpack', 'projectId': '5', 'modrinthProject': 'my-pack',
                'entries': [{'id': cf, 'versionIds': [1], 'serverPackId': server},
                            {'id': mr, 'mrGameVersions': ['1.21.1'], 'mrLoaders': ['fabric'], 'mrVersionNumber': '1.0'}]}
        out = self.client.post('/api/dry-run', json=body).json
        self.assertEqual([i['file'] for i in out['curseforge']['items']], ['pack-1.0.zip'])
        self.assertEqual(out['curseforge']['items'][0]['serverPack']['file'], 'server.zip')
        self.assertEqual([i['file'] for i in out['modrinth']['items']], ['pack-1.0.mrpack'])

    def test_duplicate_modrinth_number(self):
        a = self.add('a.jar', b'PKa').json['files'][0]['id']
        b = self.add('b.jar', b'PKb').json['files'][0]['id']
        row = {'mrGameVersions': ['1.21.1'], 'mrLoaders': ['fabric'], 'mrVersionNumber': '1.0'}
        body = {'projectType': 'mod', 'modrinthProject': 'abc', 'publishCF': False,
                'entries': [dict(row, id=a), dict(row, id=b)]}
        self.assertFalse(self.client.post('/api/dry-run', json=body).json['modrinth']['ok'])


class DependencyTests(unittest.TestCase):
    def test_five_author_upload_types(self):
        for kind in module.UPLOAD_RELATION_TYPES:
            self.assertEqual(module.validate_relations([{'slug': 'architectury-api', 'projectID': '419699', 'type': kind}], 'mod.jar'),
                             [{'slug': 'architectury-api', 'projectID': 419699, 'type': kind}])

    def test_stored_string_id_is_serialized_as_json_number(self):
        result = module.validate_relations([{'slug': 'cloth-config', 'projectID': '348521', 'type': 'optionalDependency'}], 'mod.jar')
        self.assertIs(type(result[0]['projectID']), int)
        self.assertIn('"projectID": 348521', json.dumps({'relations': {'projects': result}}))

    def test_include_rejected_by_upload_endpoint(self):
        with self.assertRaises(ValueError) as ctx:
            module.validate_relations([{'slug': 'example', 'type': 'include'}], 'mod.jar')
        self.assertIn('Include', ctx.exception.text('en'))

    def test_invalid_slug_rejected(self):
        with self.assertRaises(ValueError):
            module.validate_relations([{'slug': '', 'type': 'requiredDependency'}], 'mod.jar')


class ModrinthTests(unittest.TestCase):
    def test_dependency_mapping(self):
        relations = [{'type': 'requiredDependency', 'modrinthProjectID': 'P7dR8mSH'}]
        self.assertEqual(module.modrinth_dependencies(relations, 'example.jar'), [{'project_id': 'P7dR8mSH', 'dependency_type': 'required'}])

    def test_unsupported_dependency(self):
        with self.assertRaises(ValueError) as ctx:
            module.modrinth_dependencies([{'type': 'tool', 'modrinthProjectID': 'abcdef12'}], 'example.jar')
        self.assertIn('Modrinth', ctx.exception.text('en'))

    def test_modrinth_upload_requires_token(self):
        client = module.app.test_client()
        response = client.post('/api/upload', json={'platform': 'modrinth', 'modrinthProject': 'abcdef12', 'entries': [{}]})
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
