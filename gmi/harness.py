"""Read-only, offline and deterministic compatibility checks for agent hosts."""
import hashlib,json,platform,sys
from pathlib import Path
from . import __version__
from .research import report
from .risk import decision
from .walkforward import walk_forward


def canonical(value):
 return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def run_fixture(path):
 raw=Path(path).read_bytes();d=json.loads(raw)
 if d.get('data_class')!='SYNTHETIC':raise ValueError('compatibility fixture must be synthetic')
 a=report(d['analysis']);r=decision(d['risk']['market_hypothesis'],d['risk']['risk']);w=walk_forward(d['walkforward']['rows'],d['walkforward']['config'])
 return {'contract_version':'1','gmi_version':__version__,'fixture_content_sha256':hashlib.sha256(canonical(d)).hexdigest(),'data_class':'SYNTHETIC','analysis':{'as_of':a['as_of'],'data_quality_status':a['data_quality_status'],'model_status':a['model_status'],'final_action':a['final_action'],'managed_money_net':a['cftc']['latest']['managed_money_net'] if a['cftc']['latest'] and a['cftc']['latest']['validation_passed'] else None},'risk':r,'walkforward':w,'external_actions':'NONE','real_model_status':'NO_VALIDATED_SIGNAL'}

def verify(candidate,expected):
 actual=json.loads(Path(candidate).read_text(encoding='utf8'));gold=json.loads(Path(expected).read_text(encoding='utf8'))
 ca,ce=canonical(actual),canonical(gold);same=ca==ce
 return {'comparison_status':'MATCH' if same else 'MISMATCH','candidate_canonical_sha256':hashlib.sha256(ca).hexdigest(),'expected_canonical_sha256':hashlib.sha256(ce).hexdigest(),'diagnostic':None if same else 'JSON differs; check GMI version, input hash, algorithm and field values','scope':'output comparison only; environment origin and actual Agent execution require separate evidence'}

def environment(skill_path=None):
 checks={'python_3_10_or_later':sys.version_info >= (3,10),'gmi_import':True,'stdlib_json':True,'network_required':False}
 if skill_path is not None:
  p=Path(skill_path);checks['skill_file_exists']=p.is_file();checks['skill_entry_name']=p.name=='SKILL.md'
 return {'gmi_version':__version__,'python_version':platform.python_version(),'os':platform.system(),'checks':checks,'status':'PASS' if checks['python_3_10_or_later'] and checks['gmi_import'] and (skill_path is None or checks.get('skill_file_exists') and checks.get('skill_entry_name')) else 'FAIL','scope':'local prerequisites only, not proof of Agent installation, permission or execution'}
