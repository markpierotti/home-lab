#!/usr/bin/env python3
"""Read-only verification of the immutable collector dependency checkout."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


LOCK = Path(__file__).resolve().parents[1] / 'upstream/collector.lock.json'


def verify(checkout):
    lock = json.loads(LOCK.read_text())
    head = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    if head != lock['revision']:
        raise ValueError('checkout HEAD differs from collector.lock.json')
    status = subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain',
                                      '--untracked-files=all', '--ignored'], text=True)
    if status:
        raise ValueError('collector checkout must be clean, including untracked and ignored files')
    for relative, expected in lock['files'].items():
        path = checkout / relative
        if any(checkout.joinpath(*Path(relative).parts[:i]).is_symlink()
               for i in range(1, len(Path(relative).parts) + 1)):
            raise ValueError('symlink in source path: ' + relative)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('source hash mismatch: ' + relative)
    print('Verified collector ' + lock['collector_version'] + ' at ' + head)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('usage: verify-collector.py CHECKOUT')
        verify(Path(sys.argv[1]).resolve())
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
