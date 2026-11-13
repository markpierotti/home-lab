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

    def capture_at(self, kind, minute, day=13):
        clock = datetime.datetime(2026, 11, day, 1, minute, tzinfo=datetime.timezone.utc)
        with patch.object(capture, 'MIN_FREE', 0):
            report = capture.capture(self.vault, self.state, [(kind, self.source)], clock)
        return report['manifest'], json.loads((self.vault/report['manifest']).read_bytes())

    def test_log_append_restores_exact_bytes_without_rewriting_legacy_manifest(self):
        old, _ = self.capture_at('file', 0)
        legacy = (self.vault/old).read_bytes()
        base, _ = self.capture_at('log', 10)
        self.source.write_bytes(b'original evidence\nnext\x00')
        path, manifest = self.capture_at('log', 20)
        record = manifest['records'][0]
        self.assertEqual(record['kind'], 'log-append')
        self.assertEqual(record['previous_manifest'], base)
        self.assertEqual(gzip.decompress((self.vault/record['object']).read_bytes()), b'\nnext\x00')
        self.assertEqual(capture.restore_log(self.vault, path, str(self.source)), self.source.read_bytes())
        self.assertEqual((self.vault/old).read_bytes(), legacy)
        base_record = json.loads((self.vault/base).read_bytes())['records'][0]
        (self.vault/base_record['object']).unlink()
        with self.assertRaises(FileNotFoundError):
            capture.restore_log(self.vault, path, str(self.source))

    def test_rotation_regrowth_and_new_day_start_independent_bases(self):
        self.capture_at('log', 0)
        self.source.rename(self.root/'source.txt.1')
        self.source.write_bytes(b'original evidence with more bytes')
        _, rotated = self.capture_at('log', 10)
        self.assertEqual(rotated['records'][0]['kind'], 'log-base')
        self.source.write_bytes(b'a replacement prefix longer than the previous log')
        _, rewritten = self.capture_at('log', 20)
        self.assertEqual(rewritten['records'][0]['kind'], 'log-base')
        _, next_day = self.capture_at('log', 0, day=14)
        self.assertEqual(next_day['records'][0]['kind'], 'log-base')

    def test_rotated_whole_file_preserves_tail_across_midnight(self):
        self.capture_at('log', 50)
        self.source.write_bytes(b'original evidence\nunread tail')
        rotated = self.source.with_suffix('.1')
        self.source.rename(rotated)
        self.source.write_bytes(b'new active log')
        clock = datetime.datetime(2026, 11, 13, 14, tzinfo=datetime.timezone.utc)
        with patch.object(capture, 'MIN_FREE', 0):
            report = capture.capture(
                self.vault, self.state, [('log', self.source), ('file', rotated)], clock
            )
        manifest = json.loads((self.vault/report['manifest']).read_bytes())
        active, backup = manifest['records']
        self.assertEqual(active['kind'], 'log-base')
        self.assertEqual(backup['kind'], 'file')
        self.assertEqual(
            gzip.decompress((self.vault/backup['object']).read_bytes()),
            b'original evidence\nunread tail',
        )

    def test_budget_failure_does_not_advance_log_cursor(self):
        base, _ = self.capture_at('log', 0)
        self.source.write_bytes(b'original evidence and new bytes')
        with patch.object(capture, 'MAX_ARCHIVE', capture.archive_bytes(self.vault) + 1):
            with self.assertRaises(RuntimeError):
                self.capture_at('log', 10)
        path, manifest = self.capture_at('log', 20)
        self.assertEqual(manifest['records'][0]['previous_manifest'], base)
        self.assertEqual(capture.restore_log(self.vault, path, str(self.source)), self.source.read_bytes())

    def test_daily_sqlite_skips_same_day_and_captures_next_day(self):
        with sqlite3.connect(self.source.with_suffix('.db')) as db:
            db.execute('CREATE TABLE evidence (value TEXT)')
        self.source = self.source.with_suffix('.db')
        self.assertEqual(len(self.capture_at('sqlite-daily', 0)[1]['records']), 1)
        with sqlite3.connect(self.source) as db:
            db.execute("INSERT INTO evidence VALUES ('new')")
        same_day = self.capture_at('sqlite-daily', 10)[1]
        self.assertEqual(same_day['deferred'], 1)
        self.assertEqual(same_day['records'], [])
        self.assertEqual(len(self.capture_at('sqlite-daily', 0, day=14)[1]['records']), 1)

if __name__=='__main__': unittest.main()
