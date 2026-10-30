"""Official CFTC and FRED files; no inferred release timestamps."""
import csv, io, json, zipfile, hashlib
from datetime import datetime, timezone
from pathlib import Path
from .research import validate_observation

CFTC_FIELDS={
 ('open_interest',''):'Open_Interest_All',('reportable_long',''):'Tot_Rept_Positions_Long_All',('reportable_short',''):'Tot_Rept_Positions_Short_All',('nonreportable_long',''):'NonRept_Positions_Long_All',('nonreportable_short',''):'NonRept_Positions_Short_All',
 ('long','producer'):'Prod_Merc_Positions_Long_All',('short','producer'):'Prod_Merc_Positions_Short_All',('long','swap_dealer'):'Swap_Positions_Long_All',('short','swap_dealer'):'Swap__Positions_Short_All',('spreading','swap_dealer'):'Swap__Positions_Spread_All',('long','managed_money'):'M_Money_Positions_Long_All',('short','managed_money'):'M_Money_Positions_Short_All',('spreading','managed_money'):'M_Money_Positions_Spread_All',('long','other_reportable'):'Other_Rept_Positions_Long_All',('short','other_reportable'):'Other_Rept_Positions_Short_All',('spreading','other_reportable'):'Other_Rept_Positions_Spread_All'}
FRED={'DFII10':('real_yield_10y','US_TIPS_10Y','percent'),'DGS2':('nominal_yield_2y','US_TREASURY_2Y','percent'),'DGS10':('nominal_yield_10y','US_TREASURY_10Y','percent'),'T10YIE':('breakeven_10y','US_BREAKEVEN_10Y','percent'),'DTWEXBGS':('usd_index','DTWEXBGS','index')}

def raw_sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def metadata(meta,date):
 item=meta.get(date)
 if not item or not item.get('published_at') or not item.get('publication_evidence'): return None
 return item

def import_cftc(path,releases,retrieved_at):
 data=Path(path).read_bytes()
 if zipfile.is_zipfile(io.BytesIO(data)):
  z=zipfile.ZipFile(io.BytesIO(data)); names=[n for n in z.namelist() if n.lower().endswith(('.txt','.csv'))]
  if len(names)!=1: raise ValueError('expected one CFTC text file in zip')
  text=z.read(names[0]).decode('utf-8-sig')
 else: text=data.decode('utf-8-sig')
 reader=csv.DictReader(io.StringIO(text)); output=[]; missing=[]; matched=0
 for row in reader:
  if row.get('CFTC_Contract_Market_Code','').strip().strip("'")!='088691': continue
  matched+=1; day=row['Report_Date_as_YYYY-MM-DD'].strip(); m=metadata(releases,day)
  if not m: missing.append({'report_date':day,'reason':'missing verified release timestamp and evidence'}); continue
  if row.get('FutOnly_or_Combined','').strip().lower() not in ('futonly','futures only'): raise ValueError('input is not futures-only CFTC report')
  for (metric,category),field in CFTC_FIELDS.items():
   try: val=int(row[field].replace(',','').strip())
   except (KeyError,ValueError): raise ValueError('missing or invalid official field '+field)
   observed=day+'T00:00:00Z'
   o={'module':'cftc','metric':metric,'value':val,'unit':'contracts','instrument':'GC','market':'COMEX','observation_frequency':'weekly','source_type':'official','observed_at':observed,'report_date':observed,'published_at':m['published_at'],'publication_evidence':m['publication_evidence'],'publication_time_semantics':m.get('time_semantics','operator supplied exact publication time'),'source_update_date':m.get('updated_date'),'vintage_available_at':m.get('vintage_available_at',retrieved_at),'retrieved_at':retrieved_at,'source':'CFTC','url':'https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm','vintage':m.get('vintage','source-file-snapshot'),'contract_market_id':'088691','report_type':'disaggregated_futures_only','raw_field':field,'raw_file_sha256':hashlib.sha256(data).hexdigest()}
   if category:o['category']=category
   validate_observation(o); output.append(o)
 return {'observations':output,'matched_rows':matched,'excluded_rows':missing,'input_sha256':hashlib.sha256(data).hexdigest(),'note':'report day encoded 00:00 UTC as a date label, not an intraday observation time'}

def import_fred(path,series,releases,retrieved_at):
 if series not in FRED: raise ValueError('unsupported FRED series')
 metric,instrument,unit=FRED[series]; data=Path(path).read_bytes(); reader=csv.DictReader(io.StringIO(data.decode('utf-8-sig'))); out=[]; excluded=[]; seen={}
 for row in reader:
  day=row.get('observation_date') or row.get('DATE') or row.get('date'); value=row.get(series) if series in row else row.get('value')
  if not day: raise ValueError('missing date column')
  if value in (None,'','.'): excluded.append({'date':day,'reason':'official missing observation'}); continue
  parsed=float(value)
  if day in seen and seen[day]!=parsed:raise ValueError('conflicting FRED observations for '+series+' '+day)
  if day in seen:continue
  seen[day]=parsed
  m=metadata(releases,day)
  if not m: excluded.append({'date':day,'reason':'missing verified publication timestamp and evidence'}); continue
  o={'module':'macro','metric':metric,'value':float(value),'unit':unit,'instrument':instrument,'market':'US','observation_frequency':'daily','source_type':'official','observed_at':day+'T00:00:00Z','published_at':m['published_at'],'publication_evidence':m['publication_evidence'],'publication_time_semantics':m.get('time_semantics','operator supplied exact publication time'),'source_update_date':m.get('updated_date'),'vintage_available_at':m.get('vintage_available_at',retrieved_at),'retrieved_at':retrieved_at,'source':'FRED','url':'https://fred.stlouisfed.org/series/'+series,'vintage':m.get('vintage','source-file-snapshot'),'raw_field':series,'raw_file_sha256':hashlib.sha256(data).hexdigest()}
  validate_observation(o); out.append(o)
 return {'observations':out,'excluded_rows':excluded,'input_sha256':hashlib.sha256(data).hexdigest(),'note':'CSV snapshot is not a historical vintage; use ALFRED vintage with evidence for PIT reconstruction'}
