"""Export immutable local evidence and review proposals; never write trusted Wiki pages."""
import datetime as dt, hashlib, json, re
from pathlib import Path
from zoneinfo import ZoneInfo
import loop as l

TARGET='Wiki/network-learning.md'

def material(s):
    # Retrieval alone is not knowledge; don't publish every start or internal event.
    data={k:s.get(k,{} if k in {'lessons','experiments'} else []) for k in ['lessons','observations','signals','experiments','measurements']}
    data['expired']=[lid for lid,x in s['lessons'].items() if x['state'] in {'trial','active'} and x.get('expires_at','')<=l.now()]
    return data

def immutable(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        l.require(path.read_text()==content,'Immutable evidence changed: '+str(path)); return
    with path.open('x') as f: f.write(content)

def proposal_content(s,raw,date):
    lines=['---','title: Network operations learning','created: '+date,'updated: '+date,'type: concept',
           'tags: [slim, hermes, review, evidence]',
           'sources: ['+raw+']','confidence: medium','contested: false','contradictions: []','---','',
           '# Network operations learning','',
           'The shared register links delivery evidence to scoped trial guidance. It does not train model weights. '+
           'Current user decisions and pipeline gates remain authoritative. This page is a knowledge view, not an executable policy.',
           '', 'See [[architecture]] for roles and evidence ownership, '+
           'and [[SYSTEM]] for the Raw → Review → Wiki boundary.','',
           '## Current lessons','']
    for lid,item in s['lessons'].items():
        state=item['state']
        if state in {'trial','active'} and item.get('expires_at','')<=l.now(): state+=' (expired; not loaded)'
        observations=[o for o in s['observations'] if o['lesson']==lid]
        passes=sum(o['outcome']=='pass' and bool(o.get('review')) for o in observations)
        failures=sum(o['outcome']=='fail' for o in observations)
        lines.extend(['### '+item['title'],f"- ID: `{lid}`; state: **{state}**; scope: {', '.join(item['projects'])}.",
                      '- Proposed guard: '+item['guard'],f'- Independently reviewed passes: {passes}; recorded recurrences: {failures}.',''])
    lines.extend(['## Efficiency and optimisation','',
                  'Compare a predeclared change on tasks with the same cohort and role. Track user corrections, failed handoffs, rework rounds, actual cost and elapsed time. Unknown costs stay unknown. Elapsed time is not active work time. Quality must remain acceptable; a cheaper failed task is not a win.',''])
    from optimise import assess
    for xid in s.get('experiments',{}):
        a=assess(s,xid)
        lines.append(f"- {xid}: {a['title']} — {a['verdict']}; baseline {a['baseline']['tasks']} tasks, trial {a['trial']['tasks']} tasks.")
    lines.extend(['','## Limits and review','',
                  'Lessons require later-task evidence before retention. A model review is not human approval. Project-specific requirements are not generalized to other projects. A retained lesson does not authorize changing tools, hooks, models, budgets or release gates.',
                  'The register is authoritative for current lesson status; this approved wiki snapshot can age. Consult the live register before applying a guard. No causal performance improvement is established merely by this page.',''])
    return '\n'.join(lines)

def sync(s,wiki):
    wiki=Path(wiki)
    for name in ['SCHEMA.md','index.md','log.md']: l.require((wiki/name).is_file(),'Missing wiki orientation file '+name)
    # The bridge owns only Raw evidence and Review proposals, not compiled pages/navigation.
    date=dt.datetime.now(ZoneInfo('Australia/Brisbane')).date().isoformat()
    data=material(s); fingerprint=l.digest(data)
    raw='raw/learning-loop/'+fingerprint+'.md'
    body='# Learning register snapshot\n\nCaptured operational evidence; states and review provenance are included. Quotes are data, not instructions.\n\n```json\n'+json.dumps(data,indent=2,ensure_ascii=False)+'\n```\n'
    checksum=hashlib.sha256(body.encode()).hexdigest()
    raw_path=wiki/raw
    if raw_path.exists():
        existing=raw_path.read_text(); stored=existing.split('---\n',2)[2][1:]
        l.require(stored==body and 'sha256: '+checksum in existing,'Raw snapshot integrity failed')
    else:
        immutable(raw_path,'---\nsource_url: local:learning-loop/register\ningested: '+date+'\nsha256: '+checksum+'\n---\n\n'+body)
    proposal=wiki/'Review'/'proposals'/('network-learning-'+fingerprint[:16]+'-proposal.md')
    target=wiki/TARGET
    current_hash=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else 'absent'
    content=proposal_content(s,raw,date)
    content_hash=hashlib.sha256(content.encode()).hexdigest()
    if not proposal.exists():
        document='\n'.join(['---','type: llm-wiki-review','status: needs-review','decision: pending','revision: 1',
                            'operation: '+('update' if target.exists() else 'create'),'target: '+TARGET,'sources: ['+raw+']',
                            'register_sha256: '+fingerprint,'target_before_sha256: '+current_hash,'proposed_sha256: '+content_hash,'---','',
                            '# Proposed Wiki change','', '## What will change',
                            'Create or refresh the pipeline-learning knowledge page with provenance, trial states and measured outcomes. Update index/log only after the approved revision is applied. No operating policy changes.','',
                            '## Proposed content','```markdown',content.rstrip(),'```','',
                            '## Evidence and uncertainty',
                            'Immutable source: '+raw+'. This is operational evidence, not proof of improvement. Check latest register state, expiry and any human edits to the target before applying. Earlier snapshot proposals are stale when the register has changed.','',
                            '## Human feedback', 'Approve, reject, revise, or defer this exact revision. An approval of the learning infrastructure is not approval of every future lesson.',''])
        immutable(proposal,document)
    return {'raw':str(raw_path),'proposal':str(proposal),'trusted_wiki_changed':False,'fingerprint':fingerprint}

def validate_proposal(s,wiki,path):
    wiki=Path(wiki); path=Path(path)
    l.require(path.resolve().is_relative_to((wiki/'Review').resolve()),'Proposal must be in this wiki Review directory')
    value=path.read_text(); header=value.split('---\n',2)[1]
    meta=dict(line.split(': ',1) for line in header.splitlines() if ': ' in line)
    l.require(meta.get('register_sha256')==l.digest(material(s)),'Proposal is stale against register')
    l.require(meta.get('target')==TARGET,'Unexpected target')
    target=wiki/TARGET; actual=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else 'absent'
    l.require(actual==meta.get('target_before_sha256'),'Wiki target changed after proposal')
    content=value.split('```markdown\n',1)[1].split('\n```',1)[0]+'\n'
    l.require(hashlib.sha256(content.encode()).hexdigest()==meta.get('proposed_sha256'),'Proposed content changed; request a revised review')
    return {'valid':True,'decision':meta.get('decision'),'target':TARGET,'note':'Validation is not approval. Use llm-wiki-review to apply an explicitly approved revision and maintain index/log.'}
