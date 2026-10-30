"""Snapshot manifests and hash verification; downloaded data not redistributed."""
from pathlib import Path
import hashlib,json
SERIES=('DGS2','DGS10','DFII10','T10YIE','DTWEXBGS')

def check_manifest(cache,manifest):
 spec=json.loads(Path(manifest).read_text());out={}
 for series in SERIES:
  p=Path(cache)/(series+'.csv');expected=spec['series'][series]['sha256']
  if not p.is_file():out[series]={'status':'MISSING','expected_sha256':expected};continue
  digest=hashlib.sha256(p.read_bytes()).hexdigest();out[series]={'status':'MATCH' if digest==expected else 'MISMATCH','sha256':digest,'expected_sha256':expected}
 return {'series':out,'all_match':all(x['status']=='MATCH' for x in out.values()),'warning':'A hash match establishes file identity, not historical release time or PIT vintage.'}
