"""Verifier rejects changed or shadowing code using disposable Git checkouts."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('verify_collector', ROOT / 'scripts/verify-collector.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        (self.repo / 'collector').mkdir()
        (self.repo / 'collector/main.py').write_text('print("fixture")\n')
        (self.repo / '.gitignore').write_text('__pycache__/\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
        self.lock = self.root / 'lock.json'
        self.lock.write_text(json.dumps({'revision': self.git('rev-parse', 'HEAD').strip(),
            'collector_version': 'fixture', 'files': {'collector/main.py': hashlib.sha256(
                (self.repo / 'collector/main.py').read_bytes()).hexdigest()}}))
        context = patch.object(module, 'LOCK', self.lock)
        context.start()
        self.addCleanup(context.stop)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True)

    def test_pristine_pinned_checkout_passes(self):
        module.verify(self.repo)

    def test_tracked_change_and_untracked_shadow_are_rejected(self):
        for name in ('collector/main.py', 'collector/json.py', '__pycache__/shadow.pyc'):
            with self.subTest(name=name):
                path = self.repo / name
                original = path.read_bytes() if path.exists() else None
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'clean'):
                    module.verify(self.repo)
                path.unlink()
                if original is not None:
                    path.write_bytes(original)

    def test_symlink_parent_is_rejected_even_with_matching_hashes(self):
        external = self.root / 'external'
        (self.repo / 'collector').rename(external)
        (self.repo / 'collector').symlink_to(external, target_is_directory=True)
        real_output = module.subprocess.check_output
        def status_clean_only(args, **kwargs):
            # Exercise the explicit path check independently of Git's dirty gate.
            return '' if 'status' in args else real_output(args, **kwargs)
        with patch.object(module.subprocess, 'check_output', side_effect=status_clean_only):
            with self.assertRaisesRegex(ValueError, 'symlink in source path'):
                module.verify(self.repo)

    def test_wrong_revision_is_rejected(self):
        lock = json.loads(self.lock.read_text())
        lock['revision'] = '0' * 40
        self.lock.write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError, 'HEAD'):
            module.verify(self.repo)

    def test_actual_deployed_unit_retains_pinned_exit_contract(self):
        unit = (ROOT / 'deploy/slim/etc/systemd/system/rtax-collector.service').read_text()
        for directive in ('SuccessExitStatus=130', 'KillMode=mixed'):
            self.assertIn(directive, unit)
        codes = next(line.split("=", 1)[1].split() for line in unit.splitlines()
                     if line.startswith("RestartPreventExitStatus="))
        self.assertEqual(set(codes), {"2", "4"})


if __name__ == '__main__':
    unittest.main()
