"""Evidence-backed comparisons. Records plans and measurements; never applies pipeline changes."""
import math, statistics
import loop as l

FLOAT_METRICS={'cost_usd','elapsed_minutes','dns_latency_ms','packet_loss_percent','capture_gap_minutes','disk_growth_mib_per_day'}
METRICS=FLOAT_METRICS | {'user_corrections','handoff_failures','rework_rounds','false_alerts'}

def plan(s,p):
    x={k:l.text(p[k],k,800) for k in ['title','hypothesis','change','rollback','cohort','role','owner']}
    x['projects']=l.strings(p['projects'],'projects')
    x['metric']=p['metric']; l.require(x['metric'] in METRICS,'Unsupported metric')
    target=p['target_reduction_percent']
    l.require(type(target) in (int,float) and math.isfinite(target) and 0<target<=100,'Target reduction must be 0–100, exclusive of zero')
    x['target_reduction_percent']=target
    x['evidence']=l.evidence(p['evidence']); x['state']='proposed'; x['created_at']=l.now()
    key='X-'+l.digest({k:v for k,v in x.items() if k not in {'created_at','evidence'}})[:12]
    s.setdefault('experiments',{}).setdefault(key,x)
    return key

def authorize(s,xid,p):
    x=s['experiments'][xid]
    l.require(x['state']=='proposed','Experiment already authorized')
    x['authorization']={'actor':l.text(p['actor'],'actor',120),'scope':l.text(p['scope'],'scope'),
                        'evidence':l.evidence(p['evidence']),'at':l.now()}
    x['state']='trial_authorized'
    # An authorization record does not execute a change or substitute for the required gate.

def measure(s,p):
    x=s['experiments'][p['experiment']]
    l.require(p['phase'] in {'baseline','trial'},'Phase must be baseline or trial')
    if p['phase']=='trial': l.require(x['state']=='trial_authorized','Trial needs recorded scoped authorization')
    l.require(p['cohort']==x['cohort'] and p['role']==x['role'],'Incomparable cohort or role')
    l.require(p['project'] in x['projects'],'Project outside experiment scope')
    task=l.text(p['task'],'task',180)
    measurements=s.setdefault('measurements',[])
    l.require(not any(m['experiment']==p['experiment'] and m['task']==task and m['project']==p['project'] for m in measurements),'Task already measured; retries are not independent samples')
    values={}
    for k in METRICS:
        v=p.get(k)
        l.require(v is None or (type(v) in (int,float) and math.isfinite(v) and v>=0),'Invalid '+k)
        if k not in FLOAT_METRICS: l.require(v is None or type(v) is int,'Count must be an integer')
        if k=='packet_loss_percent': l.require(v is None or v<=100,'Packet loss cannot exceed 100 percent')
        values[k]=v
    l.require(p.get('quality_pass') is None or type(p['quality_pass']) is bool,'quality_pass must be true, false or null')
    actor=l.text(p['actor'],'actor',120)
    review=l.independent({'author':actor,'author_family':p['actor_family']},p['review'])
    m=dict(values,experiment=p['experiment'],phase=p['phase'],cohort=p['cohort'],role=p['role'],project=p['project'],
           task=task,actor=actor,quality_pass=p.get('quality_pass'),evidence=l.evidence(p['evidence']),review=review,at=l.now())
    measurements.append(m)
    return {'measured':task,'phase':p['phase']}

def assess(s,xid):
    x=s['experiments'][xid]
    rows=[m for m in s.get('measurements',[]) if m['experiment']==xid]
    result={'experiment':xid,'title':x['title'],'metric':x['metric'],'state':x['state'],'verdict':'insufficient_evidence',
            'note':'Descriptive comparison, not causal proof or permission to change policy.'}
    for phase in ['baseline','trial']:
        group=[m for m in rows if m['phase']==phase]
        values=[m[x['metric']] for m in group if m[x['metric']] is not None]
        result[phase]={'tasks':len(group),'known_values':len(values),'median':statistics.median(values) if values else None,
                       'quality_failures':sum(m['quality_pass'] is False for m in group),
                       'quality_unknown':sum(m['quality_pass'] is None for m in group)}
    if result['trial']['quality_failures']:
        result['verdict']='quality_regression_stop_trial'; return result
    if any(result[p]['tasks']<3 or result[p]['known_values']!=result[p]['tasks'] or result[p]['quality_unknown'] for p in ['baseline','trial']): return result
    baseline=result['baseline']['median']; trial=result['trial']['median']
    if baseline==0:
        result['verdict']='no_positive_baseline_to_reduce'; return result
    reduction=100*(baseline-trial)/baseline
    result['reduction_percent']=round(reduction,3)
    result['verdict']='target_observed_review_required' if reduction>=x['target_reduction_percent'] else 'target_not_met'
    return result
