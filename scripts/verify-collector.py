#!/usr/bin/env python3
"""Read-only verification of the immutable collector dependency checkout."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def verify(checkout):
    lock = json.loads((Path(__file__).resolve().parents[1] / 'upstream/collector.lock.json').read_text())
    head = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    if head != lock['revision']:
        raise ValueError('checkout HEAD differs from collector.lock.json')
    for relative, expected in lock['files'].items():
        path = checkout / relative
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
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
