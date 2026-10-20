import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('mirror',Path(__file__).parents[1]/'mirror.py')
mirror=importlib.util.module_from_spec(spec);spec.loader.exec_module(mirror)

class MirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.dest=self.root/'slim-telemetry';self.dest.mkdir()
        self.home=self.root/'state';self.home.mkdir()
        self.config={'ssh_target':'slim@192.0.2.20','vault_path':str(self.dest)}
        self.patch=patch.object(mirror,'HOME',self.home);self.patch.start();self.addCleanup(self.patch.stop)
    def receipt(self,age=0):
        (self.dest/'capture-status.json').write_text(json.dumps({'last_capture':(dt.datetime.now(dt.timezone.utc)-dt.timedelta(seconds=age)).isoformat(),'errors':[],'archive_bytes':1234}))
    def test_unsafe_target_and_symlink_destination_rejected(self):
        for host in ['-x@host','slim@host;touch /tmp/x','slim@host $(cmd)']:
            with self.assertRaises(ValueError): mirror.validate_config(dict(self.config,ssh_target=host))
        target=self.root/'real';target.mkdir();self.dest.rmdir();self.dest.symlink_to(target)
        with self.assertRaises(ValueError):mirror.validate_config(self.config)
    def test_mirror_keeps_conflicts_and_never_uses_delete(self):
        self.receipt()
        with patch.object(mirror.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')) as run:
            report=mirror.sync_once(self.config)
        command=run.call_args.args[0]
        self.assertNotIn('--delete',command);self.assertIn('--backup',command)
        self.assertTrue(any(x.startswith('--backup-dir=.sync-conflicts/') for x in command))
        self.assertEqual(report['state'],'ok')
    def test_failed_transfer_cannot_be_marked_healthy(self):
        self.receipt()
        with patch.object(mirror.subprocess,'run',return_value=subprocess.CompletedProcess([],12,'','transfer failed')):
            with self.assertRaisesRegex(RuntimeError,'pull failed'):mirror.sync_once(self.config)
        self.assertFalse((self.home/'mirror-status.json').exists())
    def test_stale_capture_is_not_healthy_and_notifies(self):
        self.receipt(age=1900)
        with patch.object(mirror.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')),patch.object(mirror,'notify') as notify:
            result=mirror.sync_once(self.config)
        self.assertEqual(result['state'],'needs-attention');notify.assert_called_once()

if __name__=='__main__':unittest.main()
