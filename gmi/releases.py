"""Fetch official archive Updated dates; use conservative availability bounds, not invented release times."""
import csv,io,json,re,zipfile,hashlib
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
from urllib.error import URLError

def report_dates(path):
 with zipfile.ZipFile(path) as z:
  names=[n for n in z.namelist() if n.endswith(('.txt','.csv'))]
  if len(names)!=1:raise ValueError('one archive member expected')
  reader=csv.DictReader(io.TextIOWrapper(z.open(names[0]),encoding='utf-8-sig'))
  return sorted({r['Report_Date_as_YYYY-MM-DD'] for r in reader if r['CFTC_Contract_Market_Code'].strip()== '088691'})

def archive_evidence(day,timeout=12):
 d=datetime.strptime(day,'%Y-%m-%d'); suffix=d.strftime('%m%d%y')
 url=f'https://www.cftc.gov/sites/default/files/files/dea/cotarchives/{d.year}/futures/other_sf{suffix}.htm'
 try:
  with urlopen(Request(url,headers={'User-Agent':'GMI research/0.3'}),timeout=timeout) as response: raw=response.read(2000000)
  html=raw.decode('utf-8',errors='replace'); page=re.sub(r'<[^>]*>',' ',html); page=' '.join(page.split())
  match=re.search(r'Updated\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})',page,re.I)
  signature=d.strftime('%B %-d, %Y')
  if not match or signature not in page: return day,{'status':'UNVERIFIED','url':url,'reason':'missing report date or Updated footer'}
  updated=datetime.strptime(match.group(1),'%B %d, %Y').date(); nextday=updated+timedelta(days=1)
  bound=datetime(nextday.year,nextday.month,nextday.day,tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
  return day,{'status':'OFFICIAL_UPDATED_DATE_BOUND','updated_date':updated.isoformat(),'published_at':bound.isoformat(),'publication_evidence':url,'time_semantics':'conservative next midnight New York upper bound; Updated date is not necessarily first release','page_sha256':hashlib.sha256(raw).hexdigest()}
 except (OSError,ValueError,URLError) as e:return day,{'status':'UNVERIFIED','url':url,'reason':type(e).__name__}

def fetch_mapping(path,workers=4):
 dates=report_dates(path)
 with ThreadPoolExecutor(max_workers=min(max(workers,1),4)) as pool: results=dict(pool.map(archive_evidence,dates))
 return {'mapping':results,'matched_reports':len(dates),'bounded_reports':sum(v['status']=='OFFICIAL_UPDATED_DATE_BOUND' for v in results.values()),'unverified_reports':sum(v['status']!='OFFICIAL_UPDATED_DATE_BOUND' for v in results.values()),'interpretation':'updated day is upper bound; not proof of actual first publication or historic vintage'}
