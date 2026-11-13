import hashlib
import json
from pathlib import Path
import unittest

class SourceManifestTests(unittest.TestCase):
    def test_adapted_learning_sources_match_manifest(self):
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'source-manifest.json').read_text())
        for name,record in manifest['files'].items():
            with self.subTest(name=name):self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),record['adapted_sha256'])

if __name__=='__main__':unittest.main()
