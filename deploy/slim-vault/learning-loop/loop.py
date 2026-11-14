#!/usr/bin/env python3
"""Local evidence-backed learning register; no network or delivery-system writes."""
import argparse, contextlib, datetime as dt, fcntl, hashlib, json, os, re, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_STORE = HERE / 'data' / 'register.json'
CAUSES = {'model_judgment', 'requirements', 'harness', 'quota', 'mixed', 'unknown'}
STATES = {'candidate', 'trial', 'active', 'suspended', 'retired'}
SECRET = re.compile(r'(?i)(sk-or-v1-|sk-|ghp_|github_pat_)[\w-]{12,}|Bearer\s+[\w.-]{12,}|(?:api[_-]?key|password|access[_-]?token)\s*[=:]\s*\S+')

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(x): return hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def require(ok, why):
    if not ok: raise ValueError(why)
def text(x, name, limit=1600):
    require(isinstance(x, str) and 0 < len(x.strip()) <= limit, 'Invalid '+name)
    require(not SECRET.search(x), 'Possible secret in '+name)
    return x.strip()
def strings(x, name):
    require(isinstance(x,list) and 0 < len(x) <= 12, 'Invalid '+name)
    return [text(v,name,100) for v in x]
def evidence(entries):
    require(isinstance(entries,list) and 0 < len(entries) <= 5, 'Need 1–5 evidence excerpts')
    result=[]
    for entry in entries:
        p=Path(entry['path']).expanduser().resolve()
        require(p.is_file() and p.stat().st_size <= 2_000_000, 'Evidence must be a small text file')
        require(p.suffix in {'.md','.txt','.json','.py','.ts','.srt'}, 'Unsupported evidence file type')
        require(not any(x in p.name.lower() for x in ['secret','credential','token','.env','auth.json']), 'Sensitive evidence file')
        quote=text(entry['quote'],'evidence quote',2000)
        source=p.read_text()
        require(quote in source, 'Evidence excerpt absent from '+str(p))
        result.append({'path':str(p),'quote':quote,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
                       'excerpt_sha256':hashlib.sha256(quote.encode()).hexdigest(),'captured_at':now()})
    return result

def fresh_store(): return {'schema_version':1,'lessons':{},'exposures':{},'observations':[], 'signals':[], 'events':[]}
@contextlib.contextmanager
def locked(path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        store=read(path) if path.exists() else fresh_store()
        yield store
        fd,tmp=tempfile.mkstemp(dir=path.parent)
        try:
            with os.fdopen(fd,'w') as f:
                json.dump(store,f,indent=2,ensure_ascii=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)

def event(s,action,lesson,detail):
    s['events'].append({'at':now(),'action':action,'lesson':lesson,'detail':detail})
def version(l):
    values={k:l[k] for k in ['title','cause','projects','roles','trigger','guard','check']}
    values['evidence']=[{k:v for k,v in e.items() if k!='captured_at'} for e in l['evidence']]
    return digest(values)
def add(s,p):
    require(len(s['lessons'])<500,'Register full; review/compact before adding more')
    l={k:text(p[k],k,limit) for k,limit in {'title':120,'trigger':250,'guard':600,'check':450,'author':120,'author_family':100}.items()}
    l['cause']=p['cause']; require(l['cause'] in CAUSES,'Invalid cause')
    for k in ['projects','roles']: l[k]=strings(p[k],k)
    l['evidence']=evidence(p['evidence']); l['state']='candidate'; l['created_at']=now()
    l['version']=version(l); lid='L-'+l['version'][:12]
    if lid in s['lessons']: return lid
    s['lessons'][lid]=l; event(s,'capture',lid,{'author':l['author']}); return lid

def independent(l,p):
    kind=p.get('review_kind')
    require(kind in {'human','independent_model'},'Review must identify human or independent_model')
    reviewer=text(p['reviewer'],'reviewer',120)
    require(reviewer!=l['author'],'Author cannot independently review their own lesson')
    family=text(p['reviewer_family'],'reviewer_family',120)
    if kind=='independent_model':
        require(family.casefold()!=l['author_family'].casefold() and family.casefold()!='unknown', 'Independent model family required')
    return {'kind':kind,'reviewer':reviewer,'family':family,'evidence':evidence(p['evidence']), 'at':now()}

def transition(s,lid,p):
    l=s['lessons'][lid]; target=p['state']; require(target in STATES,'Bad state')
    reason=text(p['reason'],'reason')
    if target=='trial':
        require(l['state']=='candidate','Only a candidate can enter trial; create a revised candidate after failure')
        # Trial is a bounded, provisional instruction; evidence review is recorded, not assumed independent.
        review={'reviewer':text(p['reviewer'],'reviewer',120),'evidence':evidence(p['evidence']),'at':now()}
        l['trial_review']=review; l['expires_at']=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=14)).isoformat()
    elif target=='active':
        require(l['state']=='trial','Only a trial can become active')
        require(l['expires_at']>now(),'Trial expired')
        obs=[o for o in s['observations'] if o['lesson']==lid and o['version']==l['version']]
        require(not any(o['outcome']=='fail' for o in obs),'Recurrence must be resolved in a revised lesson')
        passed=[o for o in obs if o['outcome']=='pass' and o.get('review')]
        require(len({o['task'] for o in passed})>=2,'Need independently reviewed passes on two distinct later tasks')
        require(len({digest([e['excerpt_sha256'] for e in o['evidence']]) for o in passed})>=2,'Reused evidence is not two trials')
        l['promotion_review']=independent(l,p)
        l['expires_at']=(dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=30)).isoformat()
    else:
        require(target in {'suspended','retired'},'Use a new candidate for revisions')
    l['state']=target; event(s,'transition',lid,{'state':target,'reason':reason})

def start(s,p):
    project=text(p['project'],'project',100); role=text(p['role'],'role',100)
    task=text(p['task'],'task',180); actor=text(p['actor'],'actor',120); family=text(p['actor_family'],'actor_family',100)
    selected=[]
    for lid,l in s['lessons'].items():
        if l['state'] not in {'trial','active'} or l['expires_at']<=now(): continue
        if project not in l['projects'] and '*' not in l['projects']: continue
        if role not in l['roles'] and '*' not in l['roles']: continue
        selected.append((lid,l))
    selected.sort(key=lambda x:(x[1]['state']!='active',x[0]))
    selected=selected[:5]
    eid='E-'+digest({'project':project,'role':role,'task':task,'actor':actor})[:16]
    if eid not in s['exposures']:
        s['exposures'][eid]={'project':project,'role':role,'task':task,'actor':actor,'actor_family':family,'at':now(),
                            'lessons':{i:l['version'] for i,l in selected}}
        event(s,'start',None,{'exposure':eid})
    # An existing task keeps its original exposure; later instruction edits cannot rewrite its history.
    exposure=s['exposures'][eid]
    guards=[{'id':i,'version':v,'state':s['lessons'][i]['state'],'trigger':s['lessons'][i]['trigger'],
             'guard':s['lessons'][i]['guard'],'check':s['lessons'][i]['check']}
            for i,v in exposure['lessons'].items() if s['lessons'][i]['state'] in {'trial','active'} and s['lessons'][i]['expires_at']>now()]
    return {'exposure':eid,'guidance':guards,'note':'Apply only when the trigger occurs. Trial guidance is provisional. Current user instructions and pipeline gates win.'}

def observe(s,p):
    e=s['exposures'][p['exposure']]; lid=p['lesson']; l=s['lessons'][lid]
    require(lid in e['lessons'],'Lesson was not loaded for this task')
    require(p['outcome'] in {'pass','fail','not_applicable','unknown'},'Invalid outcome')
    require(not any(o['exposure']==p['exposure'] and o['lesson']==lid for o in s['observations']),'Outcome already recorded; do not count retries twice')
    o={'id':'O-'+digest([p['exposure'],lid])[:16],'exposure':p['exposure'],'lesson':lid,'version':e['lessons'][lid],
       'task':e['task'],'actor':e['actor'],'actor_family':e['actor_family'],'outcome':p['outcome'],
       'note':text(p['note'],'note'),'evidence':evidence(p['evidence']),'at':now()}
    s['observations'].append(o)
    if p['outcome']=='fail' and l['state'] in {'trial','active'}:
        l['state']='suspended'; event(s,'recurrence',lid,{'observation':o['id']})
    return o['id']

def review_observation(s,oid,p):
    o=next(o for o in s['observations'] if o['id']==oid)
    require('review' not in o,'Observation already reviewed')
    # Independence is relative to both lesson author and task actor.
    require(p['reviewer']!=o['actor'],'Task actor cannot independently review their own result')
    if p.get('review_kind')=='independent_model':
        require(p['reviewer_family'].casefold()!=o['actor_family'].casefold(),'Task model family cannot self-certify')
    o['review']=independent(s['lessons'][o['lesson']],p)
    event(s,'review_observation',o['lesson'],{'observation':oid})

def import_evaluator(s,folder):
    """Import diagnostic signals only. Even valid model opinions never become instructions."""
    folder=Path(folder); ledger=read(folder/'ledger.json')
    for a in ledger.get('attempts',[]):
        key='evaluator:'+a['fingerprint']
        if any(x['id']==key for x in s['signals']): continue
        if a['status']=='started': continue
        s['signals'].append({'id':key,'case_id':a['case_id'],'status':a['status'],
                             'cost_usd':(a.get('usage') or {}).get('cost'),'error':a.get('error'),
                             'source':str((folder/'ledger.json').resolve()),'at':now(),
                             'action':'Inspect retained evidence before proposing any lesson; rejected reviews are not findings.'})
    return len(s['signals'])

def report(s):
    lines=['# Hermes learning loop','', 'Local workflow evidence, not model training or a causal benchmark.','']
    for lid,l in s['lessons'].items():
        obs=[o for o in s['observations'] if o['lesson']==lid]
        counts={k:sum(o['outcome']==k for o in obs) for k in ['pass','fail','not_applicable','unknown']}
        reviewed=sum(o['outcome']=='pass' and bool(o.get('review')) for o in obs)
        exposed=sum(lid in e['lessons'] for e in s['exposures'].values())
        state=l['state']
        if state in {'trial','active'} and l['expires_at']<=now(): state+=' (expired; not loaded)'
        lines.extend([f"## {lid}: {l['title']}",f"State: {state}. Cause: {l['cause']}.",
                      f"Tasks exposed: {exposed}; recorded outcomes: {counts}; independently reviewed passes: {reviewed}.",
                      'Guard: '+l['guard'],''])
    if s.get('experiments'):
        from optimise import assess
        lines.extend(['## Optimisation experiments',''])
        for xid in s['experiments']:
            a=assess(s,xid); lines.append(f"{xid}: {a['title']} — {a['verdict']}; baseline tasks {a['baseline']['tasks']}, trial tasks {a['trial']['tasks']}.")
        lines.append('')
    lines.extend([f"Evaluator diagnostic signals: {len(s['signals'])}. No automatic lesson promotion.",
                  'Unobserved tasks and unknown outcomes are not successes. Review identities are declared, not authenticated.',
                  'No verified reduction in mistakes until later task evidence is collected.',''])
    return '\n'.join(lines)

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--store',type=Path,default=DEFAULT_STORE)
    ap.add_argument('action',choices=['add','transition','start','observe','review-observation','import-evaluator','report','show','sync-brain','validate-brain','plan-experiment','authorize-experiment','measure','experiment-report'])
    ap.add_argument('--input',type=Path); ap.add_argument('--id'); ap.add_argument('--evaluator',type=Path)
    ap.add_argument('--wiki',type=Path,default=HERE.parent); ap.add_argument('--proposal',type=Path)
    args=ap.parse_args()
    with locked(args.store) as s:
        p=read(args.input) if args.input else {}
        if args.action=='add': out=add(s,p)
        elif args.action=='transition': transition(s,args.id,p); out=s['lessons'][args.id]['state']
        elif args.action=='start': out=start(s,p)
        elif args.action=='observe': out=observe(s,p)
        elif args.action=='review-observation': review_observation(s,args.id,p); out='review recorded'
        elif args.action=='import-evaluator': out=import_evaluator(s,args.evaluator)
        elif args.action=='sync-brain':
            from brain import sync
            out=sync(s,args.wiki)
        elif args.action=='validate-brain':
            from brain import validate_proposal
            out=validate_proposal(s,args.wiki,args.proposal)
        elif args.action in {'plan-experiment','authorize-experiment','measure','experiment-report'}:
            import optimise
            if args.action=='plan-experiment': out=optimise.plan(s,p)
            elif args.action=='authorize-experiment': optimise.authorize(s,args.id,p); out='Scoped experiment authorization recorded; no change executed'
            elif args.action=='measure': out=optimise.measure(s,p)
            else: out=optimise.assess(s,args.id)
        elif args.action=='report': out=report(s)
        else: out=s['lessons'].get(args.id) if args.id else s
        if args.action in {'add','transition','observe','review-observation','import-evaluator','plan-experiment','authorize-experiment','measure'} and args.store.resolve()==DEFAULT_STORE.resolve():
            try:
                from brain import sync
                publication=sync(s,args.wiki)
                out={'result':out,'brain':publication}
            except (ValueError,OSError) as error:
                out={'result':out,'brain_sync_error':str(error),'note':'Record saved; retry sync-brain after resolving the wiki issue.'}
    print(out if isinstance(out,str) else json.dumps(out,indent=2))
if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,StopIteration,OSError) as error: raise SystemExit('Learning loop: '+str(error))
