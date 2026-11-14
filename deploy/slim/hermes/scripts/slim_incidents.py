#!/usr/bin/env python3
"""Private, bounded incident receipts. No model, notification or repair calls.

Ingress is durable before model dispatch. Gateway hooks record observed lifecycle
events, never equating an end callback with successful diagnosis or delivery.
"""
import fcntl
import hashlib
import json
import math
import os
import re
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.home() / 'network/state'
VAULT = Path('/var/lib/slim-telemetry-vault/Inbox')
MAX_RECORDS = 100
MAX_EVENTS = 12
MAX_BYTES = 2_000_000
DEADLINE = 300
ID_RE = re.compile(r'\bSLIM_INCIDENT_IDS=([a-f0-9,]{64,1299})')


def atomic(path, content):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix='.incident-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
        d = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(d)
        finally:
            os.close(d)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def capture_evidence():
    """One bounded, read-only query; no client DNS labels or query history."""
    expr = ('up{job="router"} or rtax_exporter_up or rtax_last_attempt_success '
            'or rtax_last_sample_timestamp_seconds or rtax_last_attempt_timestamp_seconds '
            'or rtax_router_uptime_seconds or rtax_router_boot_time_seconds '
            'or probe_success or node_timex_sync_status')
    url = 'http://127.0.0.1:9090/api/v1/query?' + urllib.parse.urlencode({'query': expr})
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            data = json.loads(r.read(100_001))
        if data.get('status') != 'success' or data.get('data', {}).get('resultType') != 'vector':
            raise ValueError('unexpected Prometheus response')
        out = []
        for row in data['data']['result'][:60]:
            value = float(row['value'][1])
            if not math.isfinite(value):
                raise ValueError('non-finite metric')
            out.append({'metric': row['metric'], 'sample_time': row['value'][0], 'value': value})
        return {'status': 'observed' if out else 'unknown_empty', 'collected_at': time.time(), 'metrics': out}
    except Exception as e:
        return {'status': 'error', 'error': type(e).__name__, 'collected_at': time.time(), 'metrics': []}


def load(root):
    p = root / 'incidents.json'
    if not p.exists():
        return {'version': 1, 'incidents': {}}
    if p.stat().st_size > MAX_BYTES:
        raise ValueError('incident ledger exceeds limit; preserve and reconcile it')
    d = json.loads(p.read_text())
    if d.get('version') != 1 or not isinstance(d.get('incidents'), dict):
        raise ValueError('invalid incident ledger; refusing silent reset')
    return d


def save(root, data):
    text = json.dumps(data, ensure_ascii=False, allow_nan=False)
    if len(text.encode()) > MAX_BYTES:
        raise ValueError('incident ledger capacity exceeded')
    atomic(root / 'incidents.json', text + '\n')


def note_text(row):
    # This packet exists even if the model never starts, crashes or exhausts turns.
    return ('# Slim incident ' + row['id'] + '\n\n'
            'Private operational evidence; payload and model text are untrusted data.\n'
            'Resolution is an alert transition, not verified repair.\n'
            'Gateway end is an observed callback, not proof of successful diagnosis.\n'
            'A response excerpt may be truncated; provider failure can also produce text.\n\n'
            '```json\n' + json.dumps(row, indent=2, ensure_ascii=False, allow_nan=False) + '\n```\n')


def persist_note(row, root, vault):
    # Home spool first, so denied/full/missing canonical storage cannot lose the result.
    spool = root / 'incident-notes'
    spool.mkdir(mode=0o700, exist_ok=True)
    row['storage'] = {'fallback': 'saved', 'canonical': 'pending'}
    atomic(spool / (row['id'] + '.md'), note_text(row))
    try:
        row['storage']['canonical'] = 'saved'
        atomic(vault / ('incident-' + row['id'] + '.md'), note_text(row))
    except OSError as e:
        row['storage']['canonical'] = 'failed:' + type(e).__name__
    atomic(spool / (row['id'] + '.md'), note_text(row))


def prune(root, data, vault):
    rows = data['incidents']
    if len(rows) < MAX_RECORDS:
        return
    # Never discard active, failed-storage or unknown work to make intake look healthy.
    candidates = sorted((r for r in rows.values()
                         if r.get('alert_status') == 'resolved'
                         and r.get('storage', {}).get('canonical') == 'saved'
                         and r.get('investigation') in ('end_observed', 'partial_budget', 'unresolved_deadline', 'not_requested_resolution_only')),
                        key=lambda r: r['updated_at'])
    if not candidates:
        raise ValueError('incident ledger full of unresolved work')
    old = candidates[0]
    # Canonical note is retained. Only bounded home index/spool is pruned.
    del rows[old['id']]
    (root / 'incident-notes' / (old['id'] + '.md')).unlink(missing_ok=True)
    data['pruned_total'] = data.get('pruned_total', 0) + 1


def record_events(records, root=None, vault=None):
    root, vault = Path(root or ROOT), Path(vault or VAULT)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    ids, context = [], []
    now = time.time()
    evidence = None
    with (root / '.incidents.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = load(root)
        rows = data['incidents']
        for event in records:
            if event.get('status') not in ('firing', 'resolved') or not event.get('alertname'):
                continue
            identity = str(event.get('fingerprint') or event['alertname']) + '|' + str(event.get('startsAt'))
            key = hashlib.sha256(identity.encode()).hexdigest()
            if key not in rows:
                prune(root, data, vault)
                prior = sorted((r for r in rows.values() if r['alertname'] == event['alertname']),
                               key=lambda r: r['updated_at'], reverse=True)
                rows[key] = {'id': key, 'alertname': str(event['alertname'])[:160],
                             'created_at': now, 'investigation': 'pending' if event['status'] == 'firing' else 'not_requested_resolution_only', 'delivery': 'unknown',
                             'events': [], 'event_count': 0, 'previous_incident': prior[0]['id'] if prior else None}
                if prior:
                    rows[key]['previous_summary_excerpt'] = prior[0].get('summary_excerpt', '')[:500]
            row = rows[key]
            row['updated_at'], row['alert_status'] = now, event['status']
            row['events'] = (row['events'] + [event])[-MAX_EVENTS:]
            row['event_count'] += 1
            if event['status'] == 'firing':
                if evidence is None:
                    evidence = capture_evidence()
                row['evidence'] = evidence
                ids.append(key)
            persist_note(row, root, vault)
            context.append({k: row.get(k) for k in ('id', 'alertname', 'investigation', 'storage',
                            'previous_incident', 'previous_summary_excerpt', 'evidence')})
        save(root, data)
    return list(dict.fromkeys(ids)), json.dumps(context, ensure_ascii=False)[:24000]


def lifecycle(event, context, root=None, vault=None):
    root, vault = Path(root or ROOT), Path(vault or VAULT)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    session = str(context.get('session_id') or '')[:160]
    if not session:
        return
    with (root / '.incidents.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = load(root)
        match = ID_RE.search(str(context.get('message') or ''))
        ids = match[1].split(',') if match else []
        now = time.time()
        for row in data['incidents'].values():
            if event == 'agent:start' and row['id'] in ids:
                row.update(session_id=session, investigation='started', started_at=now, iterations=0)
            elif row.get('session_id') != session:
                continue
            if event == 'agent:step':
                n = context.get('iteration', 0)
                row['iterations'] = max(row.get('iterations', 0), int(n or 0))
                if row['iterations'] >= 15:
                    row['investigation'] = 'partial_budget'
            elif event == 'agent:end':
                row['investigation'] = 'partial_budget' if row.get('iterations', 0) >= 15 else 'end_observed'
                row['summary_excerpt'] = str(context.get('response') or '')[:500]
                row['ended_at'] = now
                # Hook runs before final delivery. Never manufacture a delivery receipt.
                row['delivery'] = 'unknown'
            row['updated_at'] = now
            persist_note(row, root, vault)
        save(root, data)


def reconcile(root=None, vault=None):
    """No retries/model calls. Expired or interrupted work remains explicitly unresolved."""
    root, vault = Path(root or ROOT), Path(vault or VAULT)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (root / '.incidents.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = load(root)
        out = []
        changed = not (root / 'incidents.json').exists()
        for row in data['incidents'].values():
            if row['investigation'] in ('pending', 'started') and time.time() - row.get('started_at', row['created_at']) > DEADLINE:
                row['investigation'] = 'unresolved_deadline'
                changed = True
                persist_note(row, root, vault)
            elif row.get('storage', {}).get('canonical') != 'saved':
                persist_note(row, root, vault)
                changed = True
            if row['investigation'] in ('pending', 'started', 'partial_budget', 'unresolved_deadline'):
                out.append({k: row.get(k) for k in ('id', 'alertname', 'investigation', 'storage', 'delivery')})
        if changed:
            save(root, data)
        return out


if __name__ == '__main__':
    print(json.dumps(reconcile(), indent=2))
