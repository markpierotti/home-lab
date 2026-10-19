"""Private recovery material stays ignored without hiding public fixtures."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class IgnoreTests(unittest.TestCase):
    def test_private_material_is_ignored_and_source_remains_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(ROOT / '.gitignore', root / '.gitignore')
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            for path in ('deploy/slim/private/config', 'backup.tar.gz', 'query.db', 'query.db-wal',
                         'query.db-shm', 'grafana.sqlite', 'id_ed25519', 'id_ed25519.pub',
                         'slim_backup', 'telegram_token', 'slim_known_hosts', '.env'):
                with self.subTest(path=path):
                    result = subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', path])
                    self.assertEqual(result.returncode, 0)
            for path in ('deploy/slim/tests/test_exporters.py', 'upstream/collector.lock.json',
                         'deploy/slim/var/lib/grafana/dashboards/router.json'):
                self.assertEqual(subprocess.run(['git', '-C', str(root), 'check-ignore', '-q', path]).returncode, 1)
