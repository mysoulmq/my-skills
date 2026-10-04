import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'skills/politics-lesson-prep/scripts'))
from model_routing import configuration,request,check
class ModelRoutingTests(unittest.TestCase):
 def test_requests_pin_model_effort_and_isolation(self):
  r=request('teaching_transform','teach','read inputs');self.assertEqual((r['model'],r['reasoning_effort'],r['fork_turns']),('gpt-6-astra','medium','none'))
  self.assertEqual(configuration('image_transcription')['reasoning_effort'],'low')
  self.assertEqual(configuration('orchestration')['model'],'gpt-6.1-sol')
 def record(self):return {'stage':'teaching_transform','acceptedRequest':request('teaching_transform','teach','inputs'),'executorResult':{'agent_id':'tool-returned-id'},'evidencePath':'private/tool-response.json'}
 def test_accepted_config_does_not_claim_runtime_attestation(self):
  r=check([self.record()]);self.assertTrue(r['pass']);self.assertIn('absent runtime',r['scope'])
 def test_silent_substitution_fails(self):
  r=self.record();r['acceptedRequest']['model']='gpt-6.1-sol';self.assertFalse(check([r])['pass'])
 def test_runtime_mismatch_fails(self):
  r=self.record();r['reportedRuntime']={'model':'gpt-6-astra','reasoning_effort':'high'};self.assertFalse(check([r])['pass'])
 def test_missing_tool_identity_fails(self):
  r=self.record();r['executorResult']={};self.assertFalse(check([r])['pass'])

 def test_empty_run_is_not_verified(self):
  self.assertFalse(check([])['pass'])
 def test_actual_task_name_response_is_supported(self):
  r=self.record();r['executorResult']={'task_name':'/root/teach'};self.assertTrue(check([r])['pass'])

 def test_unknown_stage_returns_actionable_failure(self):
  r=self.record();r['stage']='repair-new-stage';self.assertFalse(check([r])['pass'])

 def test_root_thread_receipt_uses_actual_tool_argument_names(self):
  r={'stage':'orchestration','executor':'codex.create_thread','acceptedRequest':{'model':'gpt-6.1-sol','thinking':'medium'},'executorResult':{'threadId':'returned-thread'},'evidencePath':'private/create-result.json'}
  self.assertTrue(check([r])['pass'])
  r['acceptedRequest']['thinking']='high';self.assertFalse(check([r])['pass'])
 def test_complete_run_cannot_omit_teaching_review(self):
  self.assertFalse(check([self.record()],['teaching_transform','teaching_review'])['pass'])
 def test_internal_stages_do_not_create_user_threads(self):
  r=self.record();r['executor']='codex.create_thread';r['acceptedRequest']['thinking']='medium';r['executorResult']={'threadId':'returned-thread'}
  self.assertFalse(check([r])['pass'])

 def test_unknown_runtime_text_does_not_crash_or_prove_runtime(self):
  r=self.record();r['reportedRuntime']='not reported';self.assertFalse(check([r])['pass'])
