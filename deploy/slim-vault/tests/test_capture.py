import datetime
import gzip
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('capture',Path(__file__).parents[1]/'capture.py')
capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)

class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.vault=self.root/'vault';self.vault.mkdir();self.state=self.root/'state'
        self.source=self.root/'source.txt';self.source.write_text('original evidence')
    def tearDown(self): self.temp.cleanup()
    def run_capture(self,inputs=None):
        with patch.object(capture,'MIN_FREE',0):
            return capture.capture(self.vault,self.state,inputs if inputs is not None else [('file',self.source)])
    def test_capture_survives_source_deletion(self):
        self.run_capture();self.source.unlink()
        obj=next((self.vault/'raw/objects').glob('*/*.gz'))
        self.assertEqual(gzip.decompress(obj.read_bytes()),b'original evidence')
    def test_changed_source_preserves_both_versions(self):
        self.run_capture();self.source.write_text('changed evidence');self.run_capture()
        self.assertEqual(len(list((self.vault/'raw/objects').glob('*/*.gz'))),2)
    def test_unchanged_source_deduplicates(self):
        self.run_capture();r=self.run_capture();self.assertEqual(r['changed'],0)
        self.assertEqual(len(list((self.vault/'raw/objects').glob('*/*.gz'))),1)
    def test_symlink_refused_without_recording_target(self):
        link=self.root/'link';link.symlink_to(self.source)
        with self.assertRaises(RuntimeError): self.run_capture([('file',link)])
        self.assertEqual(list((self.vault/'raw/objects').glob('*/*.gz')),[])
    def test_archive_corruption_detected(self):
        digest,relative=capture.put(self.vault,b'evidence')
        (self.vault/relative).write_bytes(gzip.compress(b'altered'))
        with self.assertRaises(RuntimeError): capture.put(self.vault,b'evidence')
    def test_storage_budget_never_prunes_previous_evidence(self):
        self.run_capture();before=set((self.vault/'raw/objects').glob('*/*.gz'))
        with patch.object(capture,'MAX_ARCHIVE',1),self.assertRaises(RuntimeError): self.run_capture()
        self.assertEqual(before,set((self.vault/'raw/objects').glob('*/*.gz')))
    def test_failed_source_is_explicit_and_good_source_is_preserved(self):
        with self.assertRaises(RuntimeError): self.run_capture([('file',self.source),('file',self.root/'missing')])
        status=json.loads((self.vault/'capture-status.json').read_text())
        self.assertEqual(len(status['errors']),1);self.assertEqual(status['changed'],1)
    def test_sqlite_snapshot_includes_committed_wal(self):
        db=self.root/'source.db'
        with sqlite3.connect(db) as s:
            s.execute('PRAGMA journal_mode=WAL');s.execute('CREATE TABLE events(value TEXT)')
            s.execute("INSERT INTO events VALUES('committed')");s.commit()
            self.run_capture([('sqlite',db)])
        obj=next((self.vault/'raw/objects').glob('*/*.gz'));restored=self.root/'restored.db'
        restored.write_bytes(gzip.decompress(obj.read_bytes()))
        with sqlite3.connect(restored) as r: self.assertEqual(r.execute('SELECT value FROM events').fetchone()[0],'committed')

if __name__=='__main__': unittest.main()
