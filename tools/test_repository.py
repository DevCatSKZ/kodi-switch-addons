import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from build_repository import archive_contents, build, https_base


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archives = self.root / 'archives'
        self.archives.mkdir()
        self.archive = self.archives / 'pvr.sample-1.0.0.zip'
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('pvr.sample/addon.xml', '<addon id="pvr.sample" version="1.0.0">'
                       '<extension point="xbmc.addon.metadata"><platform>switch</platform>'
                       '</extension></addon>')
        self.row = {'id': 'pvr.sample', 'version': '1.0.0',
                    'archive_sha256': hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                    'redistribution_review': 'pending'}
        self.catalog = self.root / 'catalog.json'
        self.catalog.write_text(json.dumps({'addons': [self.row]}))

    def test_static_repository_and_bootstrap_hashes(self):
        out = self.root / 'result'
        report = build(self.archives, self.catalog, out,
                       'https://example.invalid/kodi/piers/switch/', preview=True)
        self.assertTrue(report['bootstrap_ready'])
        self.assertFalse(report['release_approved'])
        for sidecar in out.rglob('*.sha256'):
            data = sidecar.with_suffix('').read_bytes()
            self.assertEqual(sidecar.read_text().strip(), hashlib.sha256(data).hexdigest())
        entries = ET.parse(out / 'site/addons.xml').getroot()
        self.assertEqual(len(entries), 2)
        repo = entries.find("addon[@id='repository.kodi-switch']")
        self.assertEqual(repo.findtext("extension[@point='xbmc.addon.repository']/dir/datadir"),
                         'https://example.invalid/kodi/piers/switch/')
        with zipfile.ZipFile(next((out / 'bootstrap').glob('*.zip'))) as z:
            self.assertNotIn(b'sdmc:', z.read('repository.kodi-switch/addon.xml'))

    def test_missing_host_has_no_bootstrap(self):
        report = build(self.archives, self.catalog, self.root / 'stage', preview=True)
        self.assertFalse(report['bootstrap_ready'])
        self.assertFalse((self.root / 'stage/bootstrap').exists())

    def test_separate_release_assets_and_pages_index(self):
        out = self.root / 'split'
        build(self.archives, self.catalog, out, 'https://example.org/index/', preview=True,
              package_base_url='https://example.org/releases/download/')
        self.assertTrue((out / 'release-assets/pvr.sample/pvr.sample-1.0.0.zip').exists())
        self.assertFalse(list((out / 'site').rglob('*.zip')))
        index = ET.parse(out / 'site/addons.xml').getroot()
        repo = index.find("addon[@id='repository.kodi-switch']")
        directory = repo.find("extension[@point='xbmc.addon.repository']/dir")
        self.assertEqual(directory.findtext('artdir'), 'https://example.org/index/')
        self.assertEqual(directory.findtext('datadir'), 'https://example.org/releases/download/')

    def test_unreviewed_release_is_rejected_before_writes(self):
        with self.assertRaisesRegex(ValueError, 'review incomplete'):
            build(self.archives, self.catalog, self.root / 'release', 'https://example.org/addons/')
        self.assertFalse((self.root / 'release').exists())

    def test_modified_archive_is_rejected(self):
        with self.archive.open('ab') as f:
            f.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'differs from catalog'):
            build(self.archives, self.catalog, self.root / 'bad', preview=True)

    def test_traversal_and_wrong_architecture_rejected(self):
        for name, data in [('pvr.sample/../../escape', b'x'),
                           ('pvr.sample/module.so', b'\x7fELF\x02\x01' + b'\x00' * 12 + b'\x3e\x00')]:
            with self.subTest(name=name):
                archive = self.root / 'bad.zip'
                with zipfile.ZipFile(archive, 'w') as z:
                    z.writestr(name, data)
                with self.assertRaises(ValueError):
                    archive_contents(archive, 'pvr.sample')

    def test_existing_output_and_invalid_urls_rejected(self):
        with self.assertRaisesRegex(ValueError, 'new directory'):
            build(self.archives, self.catalog, self.root, preview=True)
        for url in ('http://example.org/', 'https://example.org/no-slash',
                    'https://example.org/?token=x', 'https://example.org/#fragment'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                https_base(url)


if __name__ == '__main__':
    unittest.main()
