import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from gmi.harness import run_fixture,verify,environment
P=Path(__file__).resolve().parents[1]
class HarnessTests(unittest.TestCase):
 def test_fixed_fixture_matches_golden(self):
  x=run_fixture(P/'fixtures/gmi_portability_input.json');expected=json.loads((P/'fixtures/gmi_portability_expected.json').read_text());self.assertEqual(x,expected);self.assertEqual(x['real_model_status'],'NO_VALIDATED_SIGNAL')
 def test_verify_normalizes_json_and_detects_change(self):
  expected=P/'fixtures/gmi_portability_expected.json';obj=json.loads(expected.read_text())
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'candidate.json';p.write_text(json.dumps(obj,sort_keys=True,ensure_ascii=True))
   self.assertEqual(verify(p,expected)['comparison_status'],'MATCH');obj['gmi_version']='wrong';p.write_text(json.dumps(obj))
   self.assertEqual(verify(p,expected)['comparison_status'],'MISMATCH')
   r=subprocess.run([sys.executable,'-m','gmi','harness-verify','--candidate',str(p),'--expected',str(expected)],capture_output=True,cwd=P)
   self.assertEqual(r.returncode,1)
 def test_missing_skill_fails_prerequisite(self):
  self.assertEqual(environment('/nonexistent/SKILL.md')['status'],'FAIL')
 def test_fixture_must_be_synthetic(self):
  obj=json.loads((P/'fixtures/gmi_portability_input.json').read_text());obj['data_class']='LIVE'
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'input.json';p.write_text(json.dumps(obj))
   with self.assertRaises(ValueError):run_fixture(p)
 def test_deterministic_across_hash_seeds(self):
  import os
  with tempfile.TemporaryDirectory() as d:
   outputs=[]
   for seed in ('0','123'):
    path=Path(d)/('out'+seed+'.json');env=dict(os.environ,PYTHONHASHSEED=seed)
    r=subprocess.run([sys.executable,'-m','gmi','harness-probe','--input',str(P/'fixtures/gmi_portability_input.json'),'--output',str(path)],cwd=P,env=env,capture_output=True)
    self.assertEqual(r.returncode,0);outputs.append(json.loads(path.read_text()))
   self.assertEqual(outputs[0],outputs[1])
 def test_cli_missing_input_fails(self):
  r=subprocess.run([sys.executable,'-m','gmi','harness-probe','--input','/missing/gmi-input.json'],cwd=P,capture_output=True)
  self.assertEqual(r.returncode,2)
if __name__=='__main__':unittest.main()
