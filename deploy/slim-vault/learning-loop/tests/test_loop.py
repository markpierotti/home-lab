import copy, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import loop as l

class LoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'evidence.md'
        self.path.write_text('Original incident. Review supports bounded trial. Task one passed check. Task two passed check. Recurrence observed. Independent review passed.')
        self.s=l.fresh_store()
        self.payload={'title':'Check provenance','cause':'requirements','projects':['slim-home-lab'],'roles':['executor'],
                      'trigger':'Before changing a scoring rule','guard':'Check current stakeholder decision','check':'Handoff cites the current decision',
                      'author':'codex/author','author_family':'openai','evidence':self.ev('Original incident.')}
        self.id=l.add(self.s,self.payload)
    def ev(self,quote): return [{'path':str(self.path),'quote':quote}]
    def trial(self): l.transition(self.s,self.id,{'state':'trial','reason':'Supported','reviewer':'codex/author','evidence':self.ev('Review supports bounded trial.')})
    def start(self,task,project='slim-home-lab'):
        return l.start(self.s,{'project':project,'role':'executor','task':task,'actor':'task/'+task,'actor_family':'anthropic'})
    def review(self): return {'review_kind':'human','reviewer':'test-human','reviewer_family':'human','evidence':self.ev('Independent review passed.')}
    def outcome(self,task,quote,outcome='pass'):
        e=self.start(task)
        return l.observe(self.s,{'exposure':e['exposure'],'lesson':self.id,'outcome':outcome,'note':'Test fixture only','evidence':self.ev(quote)})
    def test_fabricated_evidence_and_secret_rejected(self):
        p=copy.deepcopy(self.payload); p['evidence']=self.ev('Absent quote')
        with self.assertRaises(ValueError): l.add(self.s,p)
        p=copy.deepcopy(self.payload); p['guard']='Bearer abcdefghijklmnopqrst'
        with self.assertRaises(ValueError): l.add(self.s,p)
    def test_candidates_not_loaded_and_project_scoped(self):
        self.assertEqual(self.start('before')['guidance'],[])
        self.trial()
        self.assertEqual(self.start('other',project='other')['guidance'],[])
        self.assertEqual(len(self.start('next')['guidance']),1)
    def test_duplicate_capture_and_task_do_not_inflate_counts(self):
        self.assertEqual(l.add(self.s,self.payload),self.id)
        self.trial(); a=self.start('one'); b=self.start('one')
        self.assertEqual(a,b); self.assertEqual(len(self.s['exposures']),1)
        self.outcome('one','Task one passed check.')
        with self.assertRaises(ValueError): self.outcome('one','Task one passed check.')
    def test_two_reviewed_tasks_and_explicit_promotion_required(self):
        self.trial()
        a=self.outcome('one','Task one passed check.'); b=self.outcome('two','Task two passed check.')
        promote=dict(self.review(),state='active',reason='Two independently reviewed tasks')
        with self.assertRaises(ValueError): l.transition(self.s,self.id,promote)
        l.review_observation(self.s,a,self.review()); l.review_observation(self.s,b,self.review())
        self.assertEqual(self.s['lessons'][self.id]['state'],'trial')
        l.transition(self.s,self.id,promote)
        self.assertEqual(self.s['lessons'][self.id]['state'],'active')
    def test_self_review_and_same_family_rejected(self):
        self.trial(); oid=self.outcome('one','Task one passed check.')
        r=self.review(); r.update(review_kind='independent_model',reviewer='other',reviewer_family='openai')
        with self.assertRaises(ValueError): l.review_observation(self.s,oid,r)
        r['reviewer_family']='anthropic'
        with self.assertRaises(ValueError): l.review_observation(self.s,oid,r)
        r=self.review(); r['reviewer']='task/one'
        with self.assertRaises(ValueError): l.review_observation(self.s,oid,r)
    def test_failure_suspends_and_expiry_stops_loading(self):
        self.trial(); self.outcome('one','Recurrence observed.','fail')
        self.assertEqual(self.s['lessons'][self.id]['state'],'suspended')
        self.assertEqual(self.start('two')['guidance'],[])
        self.s['lessons'][self.id].update(state='trial',expires_at='2000-01-01')
        self.assertEqual(self.start('three')['guidance'],[])
    def test_unknown_and_non_applicable_never_count_as_pass(self):
        self.trial(); self.outcome('one','Task one passed check.','unknown'); self.outcome('two','Task two passed check.','not_applicable')
        with self.assertRaises(ValueError): l.transition(self.s,self.id,dict(self.review(),state='active',reason='No verified passes'))
    def test_atomic_write_rolls_back_error(self):
        p=Path(self.tmp.name)/'register.json'
        with l.locked(p) as s: s['signals'].append({'id':'original'})
        before=p.read_bytes()
        with self.assertRaises(ValueError):
            with l.locked(p) as s:
                s['signals'].append({'id':'bad'}); raise ValueError('Stop')
        self.assertEqual(p.read_bytes(),before)
    def test_rejected_evaluator_import_is_only_diagnostic(self):
        p=Path(self.tmp.name)
        (p/'ledger.json').write_text(json.dumps({'attempts':[{'fingerprint':'one','case_id':'case','status':'failed','usage':{'cost':.04},'error':'Unknown evidence citation'}]}))
        l.import_evaluator(self.s,p); l.import_evaluator(self.s,p)
        self.assertEqual(len(self.s['signals']),1); self.assertEqual(len(self.s['lessons']),1)
        self.assertEqual(self.s['lessons'][self.id]['state'],'candidate')
    def test_evidence_snapshot_survives_source_update(self):
        old=self.s['lessons'][self.id]['evidence'][0]
        self.path.write_text('New requirements supersede earlier rules.')
        self.assertEqual(old['quote'],'Original incident.')
        self.assertNotEqual(old['source_sha256'],l.hashlib.sha256(self.path.read_bytes()).hexdigest())
    def test_reused_pass_evidence_does_not_enable_promotion(self):
        self.trial()
        for task in ['one','two']:
            oid=self.outcome(task,'Task one passed check.'); l.review_observation(self.s,oid,self.review())
        with self.assertRaises(ValueError): l.transition(self.s,self.id,dict(self.review(),state='active',reason='Duplicate evidence'))

if __name__=='__main__': unittest.main()
