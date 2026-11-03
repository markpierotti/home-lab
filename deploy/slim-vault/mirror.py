#!/usr/bin/env python3
"""One-way private Slim vault mirror; retain replaced files and never delete-sync."""
import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

HOME = Path.home() / 'Library/Application Support/SlimVaultMirror'
UTC = dt.timezone.utc

def validate_config(config):
    host = config['ssh_target']
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.-]*@[a-zA-Z0-9][a-zA-Z0-9_.-]*', host):
        raise ValueError('Invalid SSH target')
    dest = Path(config['vault_path']).expanduser()
    if dest.name != 'slim-telemetry' or dest.is_symlink():
        raise ValueError('Destination must be the separate slim-telemetry vault')
    return host, dest

def save(name, obj):
    p = HOME / name
    tmp = p.with_name(p.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')
        tmp.replace(p)
    finally:
        tmp.unlink(missing_ok=True)

def notify(host, message):
    command = 'sudo -n -u hermes /home/hermes/.hermes/hermes-agent/.hermes/bin/hermes send --to telegram --quiet --file -'
    r = subprocess.run(['/usr/bin/ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', host, command],
                       input=message, text=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
    if r.returncode:
        raise RuntimeError('Hermes notification failed')

def timestamp(value):
    t = dt.datetime.fromisoformat(value)
    if t.tzinfo is None:
        raise ValueError('Capture timestamp lacks timezone')
    return t

def publish(stage, dest, stamp):
    """Publish changed files without opening any existing iCloud file for read.

    rsync uses a private, non-cloud receiver. Publish through new temporary files
    and rename old copies into conflicts; evicted old contents need no hydration.
    Publish the status marker last so an interrupted copy keeps the prior marker.
    """
    files = []
    for root, dirs, names in os.walk(stage, followlinks=False):
        base = Path(root)
        for name in dirs + names:
            if (base / name).is_symlink():
                raise ValueError('Symlink in local receiver refused')
        dirs[:] = [d for d in dirs if d not in ('.obsidian', '.sync-conflicts')]
        files.extend(base / n for n in names)
    files.sort(key=lambda p: (p.relative_to(stage).as_posix() == 'capture-status.json', p.as_posix()))
    copied = 0
    for source in files:
        relative = source.relative_to(stage)
        target = dest / relative
        for i in range(1, len(relative.parts) + 1):
            if dest.joinpath(*relative.parts[:i]).is_symlink():
                raise ValueError('Symlink in reading-copy path refused')
        srcstat = source.stat()
        try:
            dststat = target.stat()
        except FileNotFoundError:
            dststat = None
        if dststat and dststat.st_size == srcstat.st_size and dststat.st_mtime_ns == srcstat.st_mtime_ns:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name('.' + target.name + '.mirror-' + uuid.uuid4().hex + '.tmp')
        backup = dest / '.sync-conflicts' / stamp / relative
        moved = False
        try:
            with source.open('rb') as reader, temp.open('xb') as writer:
                shutil.copyfileobj(reader, writer, 1024 * 1024)
                writer.flush()
                os.fsync(writer.fileno())
            shutil.copystat(source, temp)
            if dststat:
                # Check the conflict path too: never follow a local symlink.
                for i in range(1, len(backup.relative_to(dest).parts) + 1):
                    if dest.joinpath(*backup.relative_to(dest).parts[:i]).is_symlink():
                        raise ValueError('Symlink in conflict path refused')
                backup.parent.mkdir(parents=True, exist_ok=True)
                target.rename(backup)
                moved = True
            temp.replace(target)
            copied += 1
        except Exception:
            if moved and not target.exists():
                backup.rename(target)
            raise
        finally:
            temp.unlink(missing_ok=True)
    return copied

def sync_once(config):
    host, dest = validate_config(config)
    if not dest.is_dir():
        raise RuntimeError('Destination vault is missing; refusing to create a fallback')
    stamp = dt.datetime.now(UTC).strftime('%Y%m%dT%H%M%S.%fZ')
    stage = HOME / 'receiver'
    if stage.is_symlink():
        raise ValueError('Local receiver must not be a symlink')
    stage.mkdir(mode=0o700, exist_ok=True)
    # Even -W allowed openrsync to mmap an existing iCloud file. Keep rsync's
    # receiver entirely outside iCloud, then publish without reading old copies.
    command = ['/usr/bin/rsync', '-rtW', '--safe-links', '--backup',
               '--backup-dir=.sync-conflicts/' + stamp,
               '--exclude=.obsidian/', '--exclude=.sync-conflicts/',
               '--rsync-path=sudo -n /usr/bin/rsync',
               '-e', '/usr/bin/ssh -o BatchMode=yes -o ConnectTimeout=8',
               host + ':/var/lib/slim-telemetry-vault/', str(stage) + '/']
    r = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
    if r.returncode:
        raise RuntimeError('Vault pull failed: ' + r.stderr[-600:])
    status = json.loads((stage / 'capture-status.json').read_text())
    captured = timestamp(status['last_capture'])
    age = (dt.datetime.now(UTC) - captured).total_seconds()
    errorpath = stage / 'capture-error.json'
    error = json.loads(errorpath.read_text()) if errorpath.exists() else {}
    recent_error = bool(error) and timestamp(error['at']) > captured
    problem = bool(status.get('errors')) or recent_error or age > 1800 or age < -60
    manifest = status.get('manifest')
    manifest_hash = None
    if manifest:
        relative = Path(manifest)
        if relative.is_absolute() or '..' in relative.parts or relative.parts[:2] != ('raw', 'captures'):
            raise ValueError('Invalid capture manifest path')
        if any((stage.joinpath(*relative.parts[:i])).is_symlink() for i in range(1, len(relative.parts) + 1)):
            raise ValueError('Symlink capture manifest refused')
        data = (stage / relative).read_bytes()
        receipt = json.loads(data)
        if timestamp(receipt['captured_at']) != captured:
            raise ValueError('Copied status and manifest identify different captures')
        problem = problem or bool(receipt.get('errors'))
        manifest_hash = hashlib.sha256(data).hexdigest()
    published = publish(stage, dest, stamp)
    return {'last_pull': dt.datetime.now(UTC).isoformat(), 'capture_at': status['last_capture'],
            'capture_age_seconds': age, 'capture_errors': len(status.get('errors', [])),
            'recent_capture_error': recent_error, 'archive_bytes': status['archive_bytes'],
            'manifest': manifest, 'manifest_sha256': manifest_hash, 'deletion_sync': False,
            'transfer_mode': 'local-receiver-atomic-publish', 'published_files': published,
            'state': 'needs-attention' if problem else 'ok'}

def run_once(config, notifications=True):
    host, _ = validate_config(config)
    # Hold the same lock through transfer, receipt and notification transitions.
    # A second runner must not overwrite the first runner's status with 'failed'.
    with open(HOME / 'mirror.lock', 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {'state': 'skipped-busy'}
        statepath = HOME / 'mirror-status.json'
        try:
            prior = json.loads(statepath.read_text()) if statepath.exists() else {}
        except (ValueError, OSError):
            prior = {}
        try:
            report = sync_once(config)
            report['consecutive_failures'] = 0
            report['last_successful_pull'] = report['last_pull']
        except Exception as exc:
            report = {'state': 'failed', 'error': str(exc), 'checked_at': dt.datetime.now(UTC).isoformat(),
                      'last_successful_pull': prior.get('last_successful_pull') or prior.get('last_pull'),
                      'consecutive_failures': int(prior.get('consecutive_failures', 0)) + 1}
        save('mirror-status.json', report)
        message = None
        if report['state'] == 'failed' and prior.get('state') != 'failed':
            message = ('Slim vault Mac reading-copy pull failed: ' + report['error'][:300] +
                       '. This does not establish a Slim capture failure. A retry occurs on the next scheduled run while the Mac is awake and the scheduler is running.')
        elif report['state'] == 'needs-attention' and prior.get('state') != 'needs-attention':
            message = ('Mac reading-copy transfer completed, but the copied Slim capture receipt is stale, future-dated or reports source errors. Check the capture receipts; transfer success is not capture health.')
        elif report['state'] == 'ok' and prior.get('state') in ('failed', 'needs-attention'):
            message = ('Mac reading-copy pull succeeded. The latest copied Slim capture receipt is fresh and reports no source errors. This does not prove earlier capture or copy gaps were preserved; check the receipts.')
        if notifications and message:
            try:
                notify(host, message)
            except Exception as exc:
                # Notification transport failure must not falsify transfer status.
                report['notification_error'] = str(exc)
                save('mirror-status.json', report)
        return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--loop', action='store_true')
    parser.add_argument('--no-notify', action='store_true')
    args = parser.parse_args()
    config = json.loads((HOME / 'config.json').read_text())
    for _ in range(8 * 24 * 6 if args.loop else 1):
        report = run_once(config, notifications=not args.no_notify)
        print(json.dumps(report, allow_nan=False), flush=True)
        if not args.loop:
            return 1 if report['state'] == 'failed' else 0
        time.sleep(600)
    return 0

if __name__ == '__main__':
    os.umask(0o077)
    sys.exit(main())
