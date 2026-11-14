"""Regression coverage for failed storage, interrupted/budgeted work and dedupe."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'hermes/scripts'
sys.path.insert(0, str(SCRIPTS))
import slim_incidents as si


class IncidentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'state'
        self.vault = Path(self.tmp.name) / 'Inbox'
        self.vault.mkdir()
        self.fixture = patch.object(si, 'capture_evidence', return_value={'status': 'fixture', 'metrics': []})
        self.fixture.start()

    def tearDown(self):
        self.fixture.stop()
        self.tmp.cleanup()

    def send(self, status='firing', start='2026-10-21T02:12:00+10:00'):
        return si.record_events([{'status': status, 'fingerprint': 'abc', 'alertname': 'ASUS uptime reset detected',
                                  'startsAt': start}], self.root, self.vault)

    def row(self):
        return next(iter(si.load(self.root)['incidents'].values()))

    def hook(self, kind, key, **kwargs):
        si.lifecycle('agent:' + kind, {'session_id': 'fixture-session',
                     'message': 'SLIM_INCIDENT_IDS=' + key, **kwargs}, self.root, self.vault)

    def test_durable_intake_precedes_model_and_resolution_does_not_close_work(self):
        ids, _ = self.send()
        self.assertTrue((self.vault / ('incident-' + ids[0] + '.md')).exists())
        self.assertEqual(self.row()['investigation'], 'pending')
        self.send('resolved')
        self.assertEqual(self.row()['alert_status'], 'resolved')
        self.assertEqual(self.row()['investigation'], 'pending')
        self.assertEqual(self.row()['delivery'], 'unknown')

    def test_storage_denied_keeps_fallback_and_reconciles_after_recovery(self):
        real_atomic = si.atomic
        def deny(path, text):
            if Path(path).parent == self.vault:
                raise PermissionError('fixture denied')
            return real_atomic(path, text)
        with patch.object(si, 'atomic', side_effect=deny):
            ids, _ = self.send()
        row = self.row()
        self.assertEqual(row['storage']['canonical'], 'failed:PermissionError')
        self.assertTrue((self.root / 'incident-notes' / (ids[0] + '.md')).exists())
        si.reconcile(self.root, self.vault)
        self.assertEqual(self.row()['storage']['canonical'], 'saved')

    def test_resolution_received_without_firing_is_not_a_failed_investigation(self):
        ids, _ = self.send('resolved')
        self.assertEqual(ids, [])
        self.assertEqual(self.row()['investigation'], 'not_requested_resolution_only')
        with patch.object(si.time, 'time', return_value=si.time.time() + 400):
            self.assertEqual(si.reconcile(self.root, self.vault), [])

    def test_full_canonical_storage_keeps_fallback(self):
        real_atomic = si.atomic
        def full(path, text):
            if Path(path).parent == self.vault:
                raise OSError(28, 'fixture disk full')
            return real_atomic(path, text)
        with patch.object(si, 'atomic', side_effect=full):
            ids, _ = self.send()
        self.assertEqual(self.row()['storage']['canonical'], 'failed:OSError')
        self.assertTrue((self.root / 'incident-notes' / (ids[0] + '.md')).exists())

    def test_repeats_keep_event_references_and_next_episode_reuses_context(self):
        ids, _ = self.send()
        self.hook('start', ids[0])
        self.hook('end', ids[0], response='Historical partial summary')
        self.send()
        self.assertEqual(self.row()['event_count'], 2)
        newer, context = self.send(start='2026-10-21T14:12:00+10:00')
        self.assertNotEqual(ids, newer)
        self.assertIn('Historical partial summary', context)

    def test_budget_exhaustion_keeps_partial_summary_and_unknown_delivery(self):
        ids, _ = self.send()
        self.hook('start', ids[0])
        self.hook('step', ids[0], iteration=15)
        self.hook('end', ids[0], response='Partial evidence only')
        row = self.row()
        self.assertEqual(row['investigation'], 'partial_budget')
        self.assertEqual(row['summary_excerpt'], 'Partial evidence only')
        self.assertEqual(row['delivery'], 'unknown')

    def test_crash_before_or_after_start_leaves_unresolved_deadline(self):
        for started in [False, True]:
            with self.subTest(started=started):
                ids, _ = self.send()
                if started:
                    self.hook('start', ids[0])
                with patch.object(si.time, 'time', return_value=si.time.time() + 400):
                    si.reconcile(self.root, self.vault)
                self.assertEqual(self.row()['investigation'], 'unresolved_deadline')

    def test_corrupt_ledger_is_not_silently_reset(self):
        self.send()
        (self.root / 'incidents.json').write_text('{broken')
        with self.assertRaises(ValueError):
            self.send()

    def test_readonly_checker_does_not_rewrite_completed_notes_every_minute(self):
        ids, _ = self.send()
        self.hook('start', ids[0])
        self.hook('end', ids[0], response='End callback only')
        with patch.object(si, 'atomic') as write:
            si.reconcile(self.root, self.vault)
        write.assert_not_called()

    def test_bounded_records_refuse_to_evict_unresolved_work(self):
        self.send()
        with patch.object(si, 'MAX_RECORDS', 1):
            with self.assertRaisesRegex(ValueError, 'unresolved'):
                self.send(start='different')
        self.assertEqual(len(si.load(self.root)['incidents']), 1)


if __name__ == '__main__':
    unittest.main()
