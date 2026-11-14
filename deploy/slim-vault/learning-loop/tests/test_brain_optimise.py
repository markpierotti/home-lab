import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import loop as l
import brain, optimise

class BrainTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.wiki=Path(self.tmp.name)
        for name in ['SCHEMA.md','index.md','log.md']: (self.wiki/name).write_text('User-owned '+name)
        self.s=l.fresh_store()
    def test_snapshot_is_hashed_idempotent_and_cannot_publish(self):
        before={p.name:p.read_bytes() for p in self.wiki.iterdir()}
        a=brain.sync(self.s,self.wiki); b=brain.sync(self.s,self.wiki)
        self.assertEqual(a,b)
        raw=Path(a['raw']).read_text(); body=raw.split('---\n',2)[2][1:]
        self.assertIn('sha256: '+hashlib.sha256(body.encode()).hexdigest(),raw)
        self.assertFalse((self.wiki/brain.TARGET).exists())
        for name,value in before.items(): self.assertEqual((self.wiki/name).read_bytes(),value)
        self.assertTrue(brain.validate_proposal(self.s,self.wiki,a['proposal'])['valid'])
    def test_stale_register_and_changed_target_reject_proposal(self):
        a=brain.sync(self.s,self.wiki)
        self.s['signals'].append({'id':'new'})
        with self.assertRaisesRegex(ValueError,'stale'): brain.validate_proposal(self.s,self.wiki,a['proposal'])
        self.s['signals']=[]
        p=self.wiki/brain.TARGET; p.parent.mkdir(); p.write_text('User edit')
        with self.assertRaisesRegex(ValueError,'target changed'): brain.validate_proposal(self.s,self.wiki,a['proposal'])
    def test_changed_proposed_content_and_raw_fail_closed(self):
        a=brain.sync(self.s,self.wiki); p=Path(a['proposal'])
        p.write_text(p.read_text().replace('title: Network operations learning','title: Forged knowledge'))
        with self.assertRaisesRegex(ValueError,'content changed'): brain.validate_proposal(self.s,self.wiki,p)
        Path(a['raw']).write_text(Path(a['raw']).read_text().replace('register snapshot','forged snapshot'))
        with self.assertRaisesRegex(ValueError,'integrity'): brain.sync(self.s,self.wiki)
    def test_start_events_do_not_spam_wiki(self):
        a=brain.sync(self.s,self.wiki)
        l.start(self.s,{'project':'new-project','role':'web-studio','task':'intake','actor':'a','actor_family':'unknown'})
        self.assertEqual(a,brain.sync(self.s,self.wiki))

class OptimisationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'evidence.md'; self.path.write_text('Observed baseline. Scoped trial authorized. Independently reviewed measurements.')
        self.ev=lambda q:[{'path':str(self.path),'quote':q}]
        self.s=l.fresh_store()
        self.x=optimise.plan(self.s,{'title':'Fewer corrections','hypothesis':'Better source checks','change':'One checklist','rollback':'Remove checklist',
                 'cohort':'small-doc-tier1','role':'web-studio','owner':'owner','projects':['project'],'metric':'cost_usd','target_reduction_percent':20,
                 'evidence':self.ev('Observed baseline.')})
    def authorize(self): optimise.authorize(self.s,self.x,{'actor':'actual-user','scope':'Test fixture only','evidence':self.ev('Scoped trial authorized.')})
    def measurement(self,task,phase,cost=1,quality=True):
        return {'experiment':self.x,'phase':phase,'cohort':'small-doc-tier1','role':'web-studio','project':'project','task':task,'actor':'actor','actor_family':'anthropic',
                'cost_usd':cost,'quality_pass':quality,'evidence':self.ev('Independently reviewed measurements.'),
                'review':{'review_kind':'human','reviewer':'test-human','reviewer_family':'human','evidence':self.ev('Independently reviewed measurements.')}}
    def test_trial_requires_authorization_and_does_not_execute_anything(self):
        with self.assertRaisesRegex(ValueError,'authorization'): optimise.measure(self.s,self.measurement('a','trial'))
        self.authorize(); optimise.measure(self.s,self.measurement('a','trial'))
        self.assertEqual(optimise.assess(self.s,self.x)['verdict'],'insufficient_evidence')
    def test_duplicate_and_mismatched_tasks_rejected(self):
        optimise.measure(self.s,self.measurement('a','baseline'))
        with self.assertRaisesRegex(ValueError,'already measured'): optimise.measure(self.s,self.measurement('a','baseline'))
        p=self.measurement('b','baseline'); p['cohort']='large-financial-build'
        with self.assertRaisesRegex(ValueError,'Incomparable'): optimise.measure(self.s,p)
    def test_unknown_cost_is_not_free_or_a_success(self):
        self.authorize()
        for n in range(3):
            optimise.measure(self.s,self.measurement('b'+str(n),'baseline',1))
            optimise.measure(self.s,self.measurement('t'+str(n),'trial',None))
        a=optimise.assess(self.s,self.x)
        self.assertEqual(a['verdict'],'insufficient_evidence'); self.assertIsNone(a['trial']['median'])
    def test_observed_target_needs_review_and_quality_failure_wins(self):
        self.authorize()
        for n in range(3):
            optimise.measure(self.s,self.measurement('b'+str(n),'baseline',1))
            optimise.measure(self.s,self.measurement('t'+str(n),'trial',.5))
        a=optimise.assess(self.s,self.x)
        self.assertEqual(a['verdict'],'target_observed_review_required'); self.assertEqual(a['reduction_percent'],50)
        optimise.measure(self.s,self.measurement('bad','trial',.1,False))
        self.assertEqual(optimise.assess(self.s,self.x)['verdict'],'quality_regression_stop_trial')
    def test_measurement_requires_independent_review(self):
        p=self.measurement('a','baseline'); p['review']['reviewer']='actor'
        with self.assertRaises(ValueError): optimise.measure(self.s,p)
    def test_network_latency_and_loss_allow_fractions(self):
        p=self.measurement('network','baseline');p.update(dns_latency_ms=2.35,packet_loss_percent=0.2)
        optimise.measure(self.s,p)
        self.assertEqual(self.s['measurements'][0]['dns_latency_ms'],2.35)
    def test_packet_loss_outside_percentage_range_rejected(self):
        p=self.measurement('network','baseline');p['packet_loss_percent']=100.1
        with self.assertRaisesRegex(ValueError,'100 percent'): optimise.measure(self.s,p)
    def test_false_alerts_are_counts_and_unknown_latency_stays_null(self):
        p=self.measurement('network','baseline');p['false_alerts']=0.5
        with self.assertRaisesRegex(ValueError,'integer'): optimise.measure(self.s,p)
        p['false_alerts']=1;optimise.measure(self.s,p)
        self.assertIsNone(self.s['measurements'][0]['dns_latency_ms'])
if __name__=='__main__': unittest.main()
