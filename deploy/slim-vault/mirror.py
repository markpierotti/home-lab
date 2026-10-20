#!/usr/bin/env python3
"""One-way private Slim vault mirror; keeps overwritten local copies, never --delete."""
import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

HOME=Path.home()/'Library/Application Support/SlimVaultMirror'

def validate_config(config):
    host=config['ssh_target']
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.-]*@[a-zA-Z0-9][a-zA-Z0-9_.-]*',host): raise ValueError('Invalid SSH target')
    dest=Path(config['vault_path']).expanduser()
    if dest.name!='slim-telemetry' or dest.is_symlink(): raise ValueError('Destination must be the separate slim-telemetry vault')
    return host,dest

def save(name,obj):
    p=HOME/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(obj,indent=2));t.replace(p)

def notify(host,message):
    command='sudo -n -u hermes /home/hermes/.hermes/hermes-agent/.hermes/bin/hermes send --to telegram --quiet --file -'
    r=subprocess.run(['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=8',host,command],input=message,text=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90)
    if r.returncode: raise RuntimeError('Hermes notification failed')

def sync_once(config):
    host,dest=validate_config(config)
    if not dest.is_dir(): raise RuntimeError('Destination vault is missing; refusing to create a fallback')
    statepath=HOME/'mirror-status.json';prior=json.loads(statepath.read_text()) if statepath.exists() else {}
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    with open(HOME/'mirror.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        command=['/usr/bin/rsync','-rt','--safe-links','--backup','--backup-dir=.sync-conflicts/'+stamp,
                 '--exclude=.obsidian/','--exclude=.sync-conflicts/',
                 '--rsync-path=sudo -n /usr/bin/rsync','-e','/usr/bin/ssh -o BatchMode=yes -o ConnectTimeout=8',
                 host+':/var/lib/slim-telemetry-vault/',str(dest)+'/']
        r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=300)
        if r.returncode: raise RuntimeError('Vault pull failed: '+r.stderr[-600:])
        status=json.loads((dest/'capture-status.json').read_text())
        captured=dt.datetime.fromisoformat(status['last_capture'])
        age=(dt.datetime.now(dt.timezone.utc)-captured).total_seconds()
        errorpath=dest/'capture-error.json'
        error=json.loads(errorpath.read_text()) if errorpath.exists() else {}
        recent_error=bool(error) and dt.datetime.fromisoformat(error['at'])>captured
        problem=bool(status.get('errors')) or recent_error or age>1800
        report={'last_pull':dt.datetime.now(dt.timezone.utc).isoformat(),'capture_at':status['last_capture'],'capture_age_seconds':age,'capture_errors':len(status.get('errors',[])),'archive_bytes':status['archive_bytes'],'deletion_sync':False,'state':'needs-attention' if problem else 'ok'}
        save('mirror-status.json',report)
        if problem and prior.get('state')!='needs-attention':
            notify(host,'Slim vault needs attention: capture is stale or reports source failures. Existing records remain preserved. Check capture-status.json and the capture service journal; no live network changes were made.')
        elif not problem and prior.get('state') in ['needs-attention','failed']:
            notify(host,'Slim vault capture and the Mac reading copy have recovered. Check the capture receipts for any gap; recovery does not prove missing records were preserved.')
        print(json.dumps(report),flush=True)
        return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--loop',action='store_true');args=parser.parse_args()
    config=json.loads((HOME/'config.json').read_text());host,_=validate_config(config)
    for _ in range(8*24*6 if args.loop else 1):
        try: sync_once(config)
        except Exception as e:
            old=HOME/'mirror-status.json';prior=json.loads(old.read_text()) if old.exists() else {}
            print(f'{dt.datetime.now().isoformat()}: mirror failed: {e}',flush=True)
            if prior.get('state')!='failed':
                try: notify(host,'Slim vault Mac copy failed: '+str(e)[:300]+'. The Slim capture service is independent. The mirror will retry in ten minutes while this Mac runner is active.')
                except Exception: pass
            save('mirror-status.json',{'state':'failed','error':str(e),'checked_at':dt.datetime.now(dt.timezone.utc).isoformat()})
            if not args.loop: raise
        if not args.loop:return
        time.sleep(600)
    notify(host,'The initial eight-day Slim vault mirror period has ended. Slim capture continues. Review archive health/capacity and restart the Mac mirror after review.')

if __name__=='__main__':
    os.umask(0o077)
    main()
