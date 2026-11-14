#!/usr/bin/env python3
"""Private Slim evidence capture. Standard library only; no model calls or deletion."""
import argparse
import datetime as dt
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import sys
import tempfile
import uuid

VAULT = Path('/var/lib/slim-telemetry-vault')
STATE = Path('/var/lib/slim-vault-capture')
MAX_ARCHIVE = 3 * 1024**3
MIN_FREE = 2 * 1024**3
MAX_FILE = 64 * 1024**2

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with open(tmp, 'xb') as f:
            os.chmod(tmp, 0o640)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)

def json_bytes(obj):
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()

def put(vault, data):
    digest = hashlib.sha256(data).hexdigest()
    path = vault/'raw'/'objects'/digest[:2]/(digest+'.gz')
    if path.exists():
        if hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest() != digest:
            raise RuntimeError('Archived object integrity failure: '+digest)
    else:
        atomic(path, gzip.compress(data, mtime=0))
    return digest, str(path.relative_to(vault))

def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError('Not a regular, non-symlink source: '+str(path))
    with open(path, 'rb') as f:
        data = f.read(MAX_FILE+1)
    if len(data) > MAX_FILE:
        raise RuntimeError('Source exceeds 64 MiB capture limit: '+str(path))
    return data

def read_log(path, prior, day):
    """Read a bounded snapshot and verify the entire previously seen prefix."""
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as f:
        before = os.fstat(f.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError('Log source is not a regular file')
        if before.st_size > MAX_FILE:
            raise RuntimeError('Log exceeds 64 MiB capture limit')
        data = f.read(before.st_size)
        after = os.fstat(f.fileno())
        if len(data) != before.st_size or after.st_size < before.st_size:
            raise RuntimeError('Log shrank during capture; retry on next run')
        if after.st_size == before.st_size and after.st_mtime_ns != before.st_mtime_ns:
            raise RuntimeError('Log changed during capture; retry on next run')
    identity = [before.st_dev, before.st_ino]
    end = len(data)
    digest = hashlib.sha256(data).hexdigest()
    prior = prior if isinstance(prior, dict) else {}
    offset = prior.get('end', 0)
    continuation = (
        prior.get('day') == day and prior.get('identity') == identity
        and offset <= end and hashlib.sha256(data[:offset]).hexdigest() == prior.get('file_sha256')
    )
    if continuation and offset == end:
        return None, None, None
    fields = {'offset': offset if continuation else 0, 'end': end, 'file_sha256': digest}
    if continuation:
        fields['previous_manifest'] = prior['manifest']
    return data[fields['offset']:], fields, identity


def sqlite_snapshot(path, work):
    dest = work/(uuid.uuid4().hex+'.db')
    try:
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=10) as source:
            with sqlite3.connect(dest) as target:
                source.backup(target, pages=256, sleep=0.05)
                check = target.execute('PRAGMA quick_check').fetchone()[0]
                if check != 'ok':
                    raise RuntimeError('SQLite integrity failure: '+str(path))
        return read_regular(dest)
    finally:
        dest.unlink(missing_ok=True)

def sources():
    h = Path('/home/hermes/.hermes')
    specs = [
        (h/'memories','*.md'), (h/'cron/output','**/*.md'),
        (h/'logs','agent.log*'), (h/'logs','gateway.log*'),
        (h/'logs','errors.log*'), (h/'logs','scratch-prune.log*'),
        (Path('/home/hermes/network/state'),'*'),
        (Path('/home/rtax/data/samples'),'*.json'),
        (Path('/var/log/asus'),'asus.log*'),
        (Path('/var/lib/prometheus/node-exporter'),'asus*.prom'),
        (Path('/var/lib/prometheus/node-exporter'),'rtax*.prom'),
        (Path('/var/lib/prometheus/node-exporter'),'slim*.prom'),
        (Path('/var/backups/slim-vault-initial'), '**/*'),
        (VAULT/'Inbox', '*.md'),
        (VAULT/'learning-loop/data', '*.json'),
    ]
    result = {}
    for root, pattern in specs:
        for p in sorted(root.glob(pattern)):
            if p.is_file() and not p.is_symlink() and not p.name.endswith(('.lock','.tmp')):
                result[str(p)] = ('file',p)
    for name in ['outcomes.jsonl','state.json','pending_cleanup.jsonl']:
        p=Path('/home/rtax/data')/name
        if p.exists(): result[str(p)]=('file',p)
    for p in [h/'state.db',h/'cron/executions.db',h/'cron/deliveries.db',h/'cron/notepad.db']:
        if p.exists(): result[str(p)]=('sqlite',p)
    for path in [h/'logs/agent.log', Path('/var/log/asus/asus.log')]:
        if str(path) in result:
            result[str(path)] = ('log', path)
    for path in [h/'state.db', h/'cron/executions.db']:
        if str(path) in result:
            result[str(path)] = ('sqlite-daily', path)
    return list(result.values())

def archive_bytes(vault):
    return sum(p.stat().st_size for p in (vault/'raw').rglob('*') if p.is_file())

def capture(vault=VAULT, state=STATE, inputs=None, clock=None):
    now=clock or dt.datetime.now(dt.timezone.utc)
    stamp=now.strftime('%Y%m%dT%H%M%S.%fZ')
    day=now.astimezone(dt.timezone(dt.timedelta(hours=10))).strftime('%Y-%m-%d')
    if not vault.is_dir(): raise RuntimeError('Vault is missing')
    state.mkdir(parents=True,exist_ok=True,mode=0o700)
    with open(state/'capture.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        used=archive_bytes(vault)
        if used >= MAX_ARCHIVE or shutil.disk_usage(vault).free < MIN_FREE:
            raise RuntimeError('Storage guard paused capture; existing evidence was not deleted')
        previous=json.loads((state/'catalog.json').read_text()) if (state/'catalog.json').exists() else {}
        catalog=dict(previous)
        manifest={'captured_at':now.isoformat(),'timezone':'Australia/Brisbane','records':[], 'errors':[], 'unchanged':0, 'deferred':0, 'coverage':'Selected sources only; absence is not proof of no event.'}
        manifest_path = vault/'raw'/'captures'/day/(stamp+'.json')
        manifest_relative = str(manifest_path.relative_to(vault))
        with tempfile.TemporaryDirectory(prefix='sqlite-',dir=state) as td:
            for kind, path in inputs if inputs is not None else sources():
                try:
                    if path.is_symlink():
                        raise RuntimeError('Symlink source refused')
                    source = str(path)
                    prior = previous.get(source)
                    fields = {}
                    if kind == 'log':
                        data, fields, identity = read_log(path, prior, day)
                        if data is None:
                            manifest['unchanged'] += 1
                            continue
                        record_kind = 'log-append' if 'previous_manifest' in fields else 'log-base'
                    elif kind == 'sqlite-daily':
                        if isinstance(prior, dict) and prior.get('sqlite_day') == day:
                            manifest['deferred'] += 1
                            continue
                        data = sqlite_snapshot(path, Path(td))
                        record_kind = 'sqlite'
                        fields = {'cadence': 'daily'}
                    else:
                        data = sqlite_snapshot(path, Path(td)) if kind == 'sqlite' else read_regular(path)
                        record_kind = kind
                        if prior == hashlib.sha256(data).hexdigest():
                            manifest['unchanged'] += 1
                            continue
                    if used + len(data) > MAX_ARCHIVE:
                        raise RuntimeError('Archive budget would be exceeded; source deferred')
                    digest, relative = put(vault, data)
                    used += len(gzip.compress(data, mtime=0))
                    manifest['records'].append({
                        'source': source, 'kind': record_kind, 'sha256': digest,
                        'bytes': len(data), 'object': relative, **fields,
                    })
                    if kind == 'log':
                        catalog[source] = {'day': day, 'identity': identity,
                                           'end': fields['end'], 'file_sha256': fields['file_sha256'],
                                           'manifest': manifest_relative}
                    elif kind == 'sqlite-daily':
                        catalog[source] = {'sqlite_day': day, 'sha256': digest}
                    else:
                        catalog[source] = digest
                except Exception as e:
                    manifest['errors'].append({'source': str(path), 'error': str(e)})
        atomic(manifest_path,json_bytes(manifest))
        digest=hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        note=(f'---\ntitle: Capture {stamp}\ncreated: {day}\nupdated: {day}\ntype: summary\ntags: [slim, evidence]\nsources: [{str(manifest_path.relative_to(vault))}]\nconfidence: high\ncontested: false\ncontradictions: []\n---\n\n'
              f'# Evidence capture {stamp}\n\nCaptured {len(manifest["records"])} changed sources; {manifest["unchanged"]} unchanged; {len(manifest["errors"])} errors.\n\n'
              f'[Machine-readable manifest]({stamp}.json), SHA-256 `{digest}`.\n\n'
              'This records captured bytes, not independent verification of the claims inside them.\n\n'
              f'Related: [[retention-register]] · [[Review/daily/{day}]]\n')
        atomic(manifest_path.with_suffix('.md'),note.encode())
        daily=vault/'Review'/'daily'/(day+'.md')
        if not daily.exists():
            atomic(daily,(f'---\ntitle: Daily evidence review {day}\ncreated: {day}\nupdated: {day}\ntype: summary\ntags: [slim, review]\nsources: []\nconfidence: low\ncontested: false\ncontradictions: []\n---\n\n# Daily review {day}\n\n**Status: unreviewed.** These counts describe capture, not service reliability.\n\nRelated: [[index]] · [[review-plan]]\n\n## Capture receipts\n').encode())
        with open(daily,'a') as f:
            f.write(f'- [[raw/captures/{day}/{stamp}|{now.strftime("%H:%M:%S UTC")}]]: {len(manifest["records"])} changed, {manifest["unchanged"]} unchanged, {len(manifest["errors"])} errors.\n')
        atomic(state/'catalog.json',json_bytes(catalog))
        report={'last_capture':now.isoformat(),'manifest':str(manifest_path.relative_to(vault)),'changed':len(manifest['records']),'errors':manifest['errors'],'archive_bytes':archive_bytes(vault),'budget_bytes':MAX_ARCHIVE,'auto_deletion':False}
        atomic(vault/'capture-status.json',json_bytes(report))
        print(json.dumps({k:v for k,v in report.items() if k!='errors'}),flush=True)
        if manifest['errors']: raise RuntimeError(f'{len(manifest["errors"])} sources failed; see capture-status.json')
        return report

def restore_log(vault, manifest, source):
    """Rebuild one log version and verify both the chunks and final file."""
    chunks = []
    visited = set()
    expected_end = None
    file_digest = None
    while True:
        relative = Path(manifest)
        if (relative.is_absolute() or '..' in relative.parts
                or relative.parts[:2] != ('raw', 'captures') or relative in visited):
            raise ValueError('Invalid or repeated log manifest path')
        visited.add(relative)
        records = json.loads((vault/relative).read_bytes())['records']
        matches = [record for record in records if record['source'] == source]
        if len(matches) != 1 or matches[0]['kind'] not in ('log-base', 'log-append'):
            raise ValueError('Manifest has no unique log record for this source')
        record = matches[0]
        offset, end = record['offset'], record['end']
        if not 0 <= offset <= end <= MAX_FILE or (expected_end is not None and end != expected_end):
            raise ValueError('Invalid or non-contiguous log range')
        if file_digest is None:
            file_digest = record['file_sha256']
        digest = record['sha256']
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid log object digest')
        data = gzip.decompress((vault/'raw/objects'/digest[:2]/(digest+'.gz')).read_bytes())
        if (hashlib.sha256(data).hexdigest() != digest
                or len(data) != end - offset or len(data) != record['bytes']):
            raise ValueError('Log object failed integrity check')
        chunks.append(data)
        if record['kind'] == 'log-base':
            if offset != 0:
                raise ValueError('Log base must start at zero')
            break
        if offset == end:
            raise ValueError('Empty log append')
        expected_end = offset
        manifest = record['previous_manifest']
    data = b''.join(reversed(chunks))
    if hashlib.sha256(data).hexdigest() != file_digest:
        raise ValueError('Reconstructed log failed integrity check')
    return data


def main():
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['capture','read','verify','restore-log'])
    parser.add_argument('sha256_or_manifest', nargs='?')
    parser.add_argument('source', nargs='?')
    args=parser.parse_args()
    if args.command == 'restore-log':
        if not args.sha256_or_manifest or not args.source:
            parser.error('restore-log requires a vault-relative manifest path and source path')
        sys.stdout.buffer.write(restore_log(VAULT, args.sha256_or_manifest, args.source))
        return
    if args.command=='capture':
        if os.geteuid()!=0: raise PermissionError('Capture requires root; read and verify do not')
        capture();return
    if args.command=='read':
        digest=args.sha256_or_manifest or ''
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest): parser.error('A lowercase SHA-256 is required')
        data=gzip.decompress((VAULT/'raw/objects'/digest[:2]/(digest+'.gz')).read_bytes())
        if hashlib.sha256(data).hexdigest()!=digest: raise RuntimeError('Integrity failure')
        sys.stdout.buffer.write(data);return
    count=0
    for p in (VAULT/'raw/objects').glob('*/*.gz'):
        if hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()!=p.stem: raise RuntimeError('Integrity failure: '+str(p))
        count+=1
    print(f'{count} archived objects verified')

if __name__=='__main__':
    os.umask(0o027)
    try: main()
    except Exception as error:
        if sys.argv[1:2] == ['capture'] and VAULT.exists():
            atomic(VAULT/'capture-error.json',json_bytes({'at':dt.datetime.now(dt.timezone.utc).isoformat(),'error':str(error)}))
        raise
