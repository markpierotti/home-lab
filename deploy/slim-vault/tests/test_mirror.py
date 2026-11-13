import datetime as dt
import fcntl
import importlib.util
import json
import shutil
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('mirror', Path(__file__).parents[1] / 'mirror.py')
mirror = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mirror)

class MirrorRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dest = self.root / 'slim-telemetry'
        self.dest.mkdir()
        self.home = self.root / 'state'
        self.home.mkdir()
        p = patch.object(mirror, 'HOME', self.home)
        p.start()
        self.addCleanup(p.stop)
        self.config = {'ssh_target': 'slim@192.0.2.20', 'vault_path': str(self.dest)}
        self.receipt()

    def receipt(self, age=0, errors=None):
        self.capture_at = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=age)).isoformat()
        (self.dest / 'capture-status.json').write_text(json.dumps({
            'last_capture': self.capture_at, 'errors': errors or [], 'archive_bytes': 100}))

    def fake_transfer(self, *args, **kwargs):
        shutil.copytree(self.dest, self.home / 'receiver', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('.sync-conflicts', '.obsidian'))
        return subprocess.CompletedProcess(args[0], 0, '', '')

    def test_cloud_transfer_disables_delta_reads_and_preserves_backup_policy(self):
        with patch.object(mirror.subprocess, 'run', side_effect=self.fake_transfer) as run:
            report = mirror.run_once(self.config, notifications=False)
        command = run.call_args.args[0]
        self.assertIn('-rtW', command)
        self.assertEqual(command[-1], str(self.home / 'receiver') + '/')
        self.assertNotEqual(command[-1], str(self.dest) + '/')
        self.assertIn('--backup', command)
        self.assertNotIn('--inplace', command)
        self.assertFalse(any(x.startswith('--delete') for x in command))
        self.assertTrue(any(x.startswith('--backup-dir=.sync-conflicts/') for x in command))
        self.assertEqual(report['state'], 'ok')

    def test_mirror_publishes_reconstructable_log_chain(self):
        spec = importlib.util.spec_from_file_location(
            'capture', Path(__file__).parents[1] / 'capture.py'
        )
        capture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capture)
        remote = self.root / 'remote'
        remote.mkdir()
        source = self.root / 'agent.log'
        now = dt.datetime.now(dt.timezone.utc)
        with patch.object(capture, 'MIN_FREE', 0):
            source.write_bytes(b'base\n')
            capture.capture(remote, self.root / 'catalog', [('log', source)], now)
            source.write_bytes(b'base\nappend\n')
            latest = capture.capture(
                remote, self.root / 'catalog', [('log', source)],
                now + dt.timedelta(microseconds=1),
            )

        def transfer(command, **kwargs):
            shutil.copytree(remote, self.home / 'receiver', dirs_exist_ok=True)
            return subprocess.CompletedProcess(command, 0, '', '')

        with patch.object(mirror.subprocess, 'run', side_effect=transfer):
            report = mirror.run_once(self.config, notifications=False)
        self.assertEqual(report['state'], 'ok')
        manifest = latest['manifest']
        record = json.loads((self.dest / manifest).read_bytes())['records'][0]
        self.assertEqual(record['kind'], 'log-append')
        self.assertEqual(
            capture.restore_log(self.dest, manifest, str(source)), b'base\nappend\n'
        )

    def test_publish_never_reads_evicted_old_contents_and_preserves_them(self):
        stage = self.home / 'receiver'
        stage.mkdir()
        (stage / 'note').write_text('new canonical contents')
        target = self.dest / 'note'
        target.write_text('old local contents')
        (self.dest / 'local-only').write_text('retain')
        original = Path.open
        def guarded(path, mode='r', *args, **kwargs):
            if path == target and 'r' in mode:
                raise OSError(11, 'Resource deadlock avoided')
            return original(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', guarded):
            self.assertEqual(mirror.publish(stage, self.dest, 'fixture'), 1)
        self.assertEqual(target.read_text(), 'new canonical contents')
        self.assertEqual((self.dest / '.sync-conflicts/fixture/note').read_text(), 'old local contents')
        self.assertEqual((self.dest / 'local-only').read_text(), 'retain')

    def test_failed_publish_retains_old_status_marker(self):
        stage = self.home / 'receiver'
        stage.mkdir()
        (stage / 'a-note').write_text('new')
        (stage / 'capture-status.json').write_text('new marker')
        original = Path.replace
        def fail_note(path, target):
            if Path(target).name == 'a-note': raise OSError('publication denied')
            return original(path, target)
        before = (self.dest / 'capture-status.json').read_bytes()
        with patch.object(Path, 'replace', fail_note):
            with self.assertRaisesRegex(OSError, 'publication denied'):
                mirror.publish(stage, self.dest, 'fixture')
        self.assertEqual((self.dest / 'capture-status.json').read_bytes(), before)

    def test_publish_restores_prior_copy_if_final_rename_fails(self):
        stage = self.home / 'receiver'
        stage.mkdir()
        (stage / 'note').write_text('new canonical contents')
        target = self.dest / 'note'
        target.write_text('old local contents')
        with patch.object(Path, 'replace', side_effect=OSError('rename denied')):
            with self.assertRaises(OSError): mirror.publish(stage, self.dest, 'fixture')
        self.assertEqual(target.read_text(), 'old local contents')

    def test_publish_rejects_symlink_paths_and_skips_unchanged_files(self):
        stage = self.home / 'receiver'
        stage.mkdir()
        (stage / 'note').write_text('canonical')
        mirror.publish(stage, self.dest, 'first')
        self.assertEqual(mirror.publish(stage, self.dest, 'second'), 0)
        (self.dest / 'note').unlink()
        outside = self.root / 'outside'
        outside.write_text('retain')
        (self.dest / 'note').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            mirror.publish(stage, self.dest, 'third')
        self.assertEqual(outside.read_text(), 'retain')

    def test_actual_rsync_keeps_replaced_copy_and_local_only_file(self):
        src = self.root / 'source'
        src.mkdir()
        (src / 'note').write_text('new remote note longer')
        (self.dest / 'note').write_text('local edit')
        (self.dest / 'local-only').write_text('retain')
        subprocess.run(['/usr/bin/rsync', '-rtW', '--safe-links', '--backup',
                        '--backup-dir=.sync-conflicts/fixture', str(src) + '/', str(self.dest) + '/'],
                       check=True, capture_output=True)
        self.assertEqual((self.dest / 'note').read_text(), 'new remote note longer')
        self.assertEqual((self.dest / '.sync-conflicts/fixture/note').read_text(), 'local edit')
        self.assertEqual((self.dest / 'local-only').read_text(), 'retain')

    def test_failed_pull_preserves_last_success_and_does_not_claim_capture_failure(self):
        mirror.save('mirror-status.json', {'state': 'ok', 'last_pull': 'previous'})
        bad = subprocess.CompletedProcess([], 12, '', 'Resource deadlock avoided')
        with patch.object(mirror.subprocess, 'run', return_value=bad), patch.object(mirror, 'notify') as n:
            report = mirror.run_once(self.config)
        self.assertEqual(report['state'], 'failed')
        self.assertEqual(report['last_successful_pull'], 'previous')
        self.assertIn('does not establish a Slim capture failure', n.call_args.args[1])
        self.assertNotIn('in ten minutes', n.call_args.args[1])

    def test_repeated_failure_does_not_notify_again(self):
        mirror.save('mirror-status.json', {'state': 'failed', 'consecutive_failures': 1})
        with patch.object(mirror.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'denied')), patch.object(mirror, 'notify') as n:
            report = mirror.run_once(self.config)
        self.assertEqual(report['consecutive_failures'], 2)
        n.assert_not_called()

    def test_busy_runner_cannot_overwrite_status_or_send_false_failure(self):
        mirror.save('mirror-status.json', {'state': 'ok', 'marker': 'unchanged'})
        before = (self.home / 'mirror-status.json').read_bytes()
        with open(self.home / 'mirror.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with patch.object(mirror, 'notify') as n:
                report = mirror.run_once(self.config)
        self.assertEqual(report['state'], 'skipped-busy')
        self.assertEqual((self.home / 'mirror-status.json').read_bytes(), before)
        n.assert_not_called()

    def test_recovery_message_only_claims_transfer_and_latest_receipt(self):
        mirror.save('mirror-status.json', {'state': 'failed'})
        with patch.object(mirror.subprocess, 'run', side_effect=self.fake_transfer), patch.object(mirror, 'notify') as n:
            report = mirror.run_once(self.config)
        self.assertEqual(report['state'], 'ok')
        self.assertIn('Mac reading-copy pull succeeded', n.call_args.args[1])
        self.assertIn('does not prove earlier capture or copy gaps', n.call_args.args[1])

    def test_notification_failure_does_not_turn_good_transfer_into_failed(self):
        mirror.save('mirror-status.json', {'state': 'failed'})
        with patch.object(mirror.subprocess, 'run', side_effect=self.fake_transfer), patch.object(mirror, 'notify', side_effect=RuntimeError('unreachable')):
            report = mirror.run_once(self.config)
        self.assertEqual(report['state'], 'ok')
        self.assertEqual(report['notification_error'], 'unreachable')

    def test_stale_and_future_receipts_never_healthy(self):
        for age in (1900, -120):
            self.receipt(age=age)
            with patch.object(mirror.subprocess, 'run', side_effect=self.fake_transfer):
                report = mirror.run_once(self.config, notifications=False)
            self.assertEqual(report['state'], 'needs-attention')

    def test_historical_error_is_not_current_but_new_error_is(self):
        for offset, expected in ((-3600, 'ok'), (60, 'needs-attention')):
            t = dt.datetime.fromisoformat(self.capture_at) + dt.timedelta(seconds=offset)
            (self.dest / 'capture-error.json').write_text(json.dumps({'at': t.isoformat(), 'error': 'fixture'}))
            with patch.object(mirror.subprocess, 'run', side_effect=self.fake_transfer):
                report = mirror.run_once(self.config, notifications=False)
            self.assertEqual(report['state'], expected)

    def test_incomplete_copy_missing_referenced_manifest_is_failed(self):
        p = self.dest / 'capture-status.json'
        d = json.loads(p.read_text())
        d['manifest'] = 'raw/captures/day/missing.json'
        p.write_text(json.dumps(d))
        with patch.object(mirror.subprocess, 'run', side_effect=self.fake_transfer):
            report = mirror.run_once(self.config, notifications=False)
        self.assertEqual(report['state'], 'failed')

    def test_manifest_matches_status_and_is_hashed(self):
        relative = 'raw/captures/day/current.json'
        p = self.dest / relative
        p.parent.mkdir(parents=True)
        p.write_text(json.dumps({'captured_at': self.capture_at, 'errors': []}))
        s = self.dest / 'capture-status.json'
        d = json.loads(s.read_text())
        d['manifest'] = relative
        s.write_text(json.dumps(d))
        with patch.object(mirror.subprocess, 'run', side_effect=self.fake_transfer):
            report = mirror.run_once(self.config, notifications=False)
        self.assertEqual(report['state'], 'ok')
        self.assertEqual(len(report['manifest_sha256']), 64)

    def test_missing_vault_and_unsafe_ssh_target_refused(self):
        for host in ('-x@host', 'slim@host; touch /tmp/x'):
            with self.assertRaises(ValueError):
                mirror.validate_config(dict(self.config, ssh_target=host))
        self.dest.rename(self.root / 'kept')
        report = mirror.run_once(self.config, notifications=False)
        self.assertEqual(report['state'], 'failed')
        self.assertFalse(self.dest.exists())

if __name__ == '__main__':
    unittest.main()
