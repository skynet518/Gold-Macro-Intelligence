import csv,tempfile,unittest,json
from pathlib import Path
from datetime import date
from gmi.events import load_prices,compute_events,last_before,macro_phase,study
P=Path(__file__).resolve().parents[1]
class V4Tests(unittest.TestCase):
 def test_censor_and_threshold_and_recovery(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'p.csv';p.write_text('month,price_usd_troy_oz\n2020-01,100\n2020-02,89\n2020-03,80\n2020-04,100\n2020-05,85\n')
   events,_=compute_events(load_prices(p),.1)
   self.assertEqual(events[0]['first_threshold_month'],'2020-02');self.assertEqual(events[0]['trough_to_recovery_months'],1);self.assertIsNone(events[0]['fall_trading_days']);self.assertTrue(events[1]['right_censored']);self.assertIsNone(events[1]['recovery_month'])
 def test_missing_month_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'p.csv';p.write_text('month,price_usd_troy_oz\n2020-01,100\n2020-03,80\n')
   with self.assertRaises(ValueError):load_prices(p)
 def test_last_before_does_not_peek(self):
  r=last_before([(date(2020,1,29),1),(date(2020,2,1),9)],date(2020,1,31))
  self.assertEqual(r['value'],1);self.assertEqual(r['observation_date'],'2020-01-29')
 def test_stale_macro_is_missing(self):
  x=last_before([(date(2020,1,1),1)],date(2020,1,31));self.assertEqual(x['status'],'STALE');self.assertIsNone(x['value'])
 def test_cannot_cross_series_break(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'p.csv';p.write_text('month,price_usd_troy_oz\n2025-06,100\n2025-07,80\n')
   with self.assertRaisesRegex(ValueError,'break'):study(p,p,d,[],'2026-10-30T05:00:00Z')
 @unittest.skipUnless((P/'evidence/gmi_historical_events_2026-10.json').is_file(), 'External data integration: authorized source/evidence files not included')
 def test_real_historical_events_and_right_censor(self):
  result=json.loads((P/'evidence/gmi_historical_events_2026-10.json').read_text());events=result['events'];self.assertEqual(events[0]['peak_month'],'1974-12');self.assertEqual(events[0]['trough_month'],'1976-08');self.assertTrue(events[-1]['right_censored']);self.assertTrue(events[-1]['segment_left_truncated']);self.assertIsNone(events[0]['fall_trading_days']);self.assertIsNone(events[0]['macro']['DFII10']['peak_to_trough'])
if __name__=='__main__':unittest.main()
