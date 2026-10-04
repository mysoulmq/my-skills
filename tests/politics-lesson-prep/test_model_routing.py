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
