import argparse, csv, json, sys
from pathlib import Path
from .core import report, drawdowns, survival, backtest, validate_observation, conditional_drawdowns
from .adapters import import_cftc, import_fred
from .research import validate_price_contract
from .update import fetch_fred,build_report,render_markdown
from .releases import fetch_mapping
from .events import study,render_study,load_prices,macro_data,get_cftc_series
from .factors import research,render_research
from .snapshots import check_manifest
from .audit import real_audit,render_audit
from .walkforward import walk_forward
from .risk import decision
from .harness import run_fixture,verify,environment

def main():
    p=argparse.ArgumentParser(prog='gmi'); sub=p.add_subparsers(dest='command',required=True)
    for name in ('analyze','drawdowns','backtest'):
        s=sub.add_parser(name); s.add_argument('input'); s.add_argument('--output')
        if name=='drawdowns': s.add_argument('--threshold',type=float,default=.1)
    s=sub.add_parser('import-csv'); s.add_argument('input'); s.add_argument('--output',required=True)
    
    s=sub.add_parser('import-cftc'); s.add_argument('input'); s.add_argument('--releases',required=True); s.add_argument('--retrieved-at',required=True); s.add_argument('--output',required=True)
    s=sub.add_parser('import-fred'); s.add_argument('input'); s.add_argument('--series',required=True); s.add_argument('--releases',required=True); s.add_argument('--retrieved-at',required=True); s.add_argument('--output',required=True)
    s=sub.add_parser('release-map'); s.add_argument('input'); s.add_argument('--output',required=True)
    s=sub.add_parser('update-report'); s.add_argument('--cftc',required=True); s.add_argument('--releases',required=True); s.add_argument('--fred-cache',required=True); s.add_argument('--fetch-fred',action='store_true'); s.add_argument('--refresh',action='store_true'); s.add_argument('--output',required=True); s.add_argument('--supplement'); s.add_argument('--markdown')
    s=sub.add_parser('event-study'); s.add_argument('--fixing',required=True); s.add_argument('--spot',required=True); s.add_argument('--fred-cache'); s.add_argument('--fred-anchors'); s.add_argument('--cftc',action='append',nargs=2,default=[]); s.add_argument('--threshold',type=float,default=0.1); s.add_argument('--output',required=True); s.add_argument('--markdown')
    s=sub.add_parser('factor-research'); s.add_argument('--weights'); s.add_argument('--factor-input'); s.add_argument('--fixing',required=True); s.add_argument('--spot',required=True); s.add_argument('--fred-cache',required=True); s.add_argument('--cftc',action='append',nargs=2,default=[]); s.add_argument('--output',required=True); s.add_argument('--markdown')
    s=sub.add_parser('snapshot-fetch'); s.add_argument('--cache',required=True); s.add_argument('--refresh',action='store_true'); s.add_argument('--output')
    s=sub.add_parser('snapshot-check'); s.add_argument('--cache',required=True); s.add_argument('--manifest',required=True); s.add_argument('--output')
    s=sub.add_parser('walk-forward'); s.add_argument('input'); s.add_argument('--output')
    s=sub.add_parser('risk-check'); s.add_argument('input'); s.add_argument('--output')
    s=sub.add_parser('real-audit'); s.add_argument('--cache',required=True); s.add_argument('--manifest',required=True); s.add_argument('--fixing',required=True); s.add_argument('--spot',required=True); s.add_argument('--output',required=True); s.add_argument('--markdown')
    s=sub.add_parser('harness-probe'); s.add_argument('--input',required=True); s.add_argument('--output')
    s=sub.add_parser('harness-verify'); s.add_argument('--candidate',required=True); s.add_argument('--expected',required=True); s.add_argument('--output')
    s=sub.add_parser('env-check'); s.add_argument('--skill'); s.add_argument('--output')
    a=p.parse_args()
    try:
        if a.command=='harness-probe':
            result=run_fixture(a.input)
        elif a.command=='harness-verify':
            result=verify(a.candidate,a.expected)
        elif a.command=='env-check':
            result=environment(a.skill)
        elif a.command=='snapshot-fetch':
            result=fetch_fred(a.cache,a.refresh)
        elif a.command=='snapshot-check':
            result=check_manifest(a.cache,a.manifest)
        elif a.command=='walk-forward':
            d=json.loads(Path(a.input).read_text());result=walk_forward(d['rows'],d['config'])
        elif a.command=='risk-check':
            d=json.loads(Path(a.input).read_text());result=decision(d.get('market_hypothesis','observe'),d.get('risk'))
        elif a.command=='real-audit':
            result=real_audit(a.cache,a.manifest,a.fixing,a.spot)
            if a.markdown:Path(a.markdown).write_text(render_audit(result),encoding='utf-8')
        elif a.command=='factor-research':
            from datetime import datetime,timezone
            prices={'fixing':load_prices(a.fixing),'spot':load_prices(a.spot)}
            if prices['fixing'][-1]['month']>='2025-06' or prices['spot'][0]['month']<'2025-06': raise ValueError('price series crosses source-definition break')
            macro=macro_data(a.fred_cache); positions,sources=get_cftc_series(a.cftc,datetime.now(timezone.utc).isoformat())
            import hashlib
            info={'fred':{k:v['source'] for k,v in macro.items()},'cftc':sources,'price_sha256':{k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in [('fixing',a.fixing),('spot',a.spot)]}}
            weights=json.loads(Path(a.weights).read_text()) if a.weights else None
            supplement=json.loads(Path(a.factor_input).read_text()) if a.factor_input else None
            result=research(prices,macro,positions,info,weights,supplement)
            if a.markdown: Path(a.markdown).write_text(render_research(result),encoding='utf-8')
        elif a.command=='event-study':
            from datetime import datetime,timezone
            
            if bool(a.fred_cache)==bool(a.fred_anchors): raise ValueError('choose exactly one of --fred-cache or --fred-anchors')
            result=study(a.fixing,a.spot,a.fred_cache,a.cftc,datetime.now(timezone.utc).isoformat(),a.threshold,a.fred_anchors)
            if a.markdown: Path(a.markdown).write_text(render_study(result),encoding='utf-8')
        elif a.command=='release-map':
            result=fetch_mapping(a.input)
        elif a.command=='update-report':
            from datetime import datetime,timezone,timedelta
            if a.fetch_fred: fetch_fred(a.fred_cache,a.refresh)
            # Report clock is after all input retrievals; users cannot backdate snapshot mode.
            at=(datetime.now(timezone.utc)+timedelta(seconds=1)).isoformat()
            result=build_report(a.cftc,a.releases,a.fred_cache,at,a.output,a.supplement)
            if a.markdown: Path(a.markdown).write_text(render_markdown(result),encoding='utf-8')
        elif a.command in ('import-cftc','import-fred'):
            releases=json.loads(Path(a.releases).read_text(encoding='utf-8'))
            result=import_cftc(a.input,releases,a.retrieved_at) if a.command=='import-cftc' else import_fred(a.input,a.series,releases,a.retrieved_at)
        elif a.command=='import-csv':
            with open(a.input,encoding='utf-8-sig',newline='') as f: data=list(csv.DictReader(f))
            for row in data:
                row['value']=float(row['value']); validate_observation(row)
            result={'observations':data}
        else:
            data=json.loads(Path(a.input).read_text(encoding='utf-8'))
            if a.command in ('drawdowns','backtest'): validate_price_contract(data)
            if a.command=='analyze': result=report(data)
            elif a.command=='backtest': result=backtest(data)
            else:
                events=drawdowns(data['prices'],a.threshold); result={'threshold':a.threshold,'episodes':events,'survival':survival(events),'conditional_from_first_crossing':conditional_drawdowns(data['prices'],a.threshold),'units':'calendar days','note':'Retrospective threshold selection; survival starts at peak, including time before threshold crossing. Research use only.'}
        output=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        if a.output: Path(a.output).write_text(output,encoding='utf-8')
        else: print(output,end='')
    except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as e:
        print('gmi: '+str(e),file=sys.stderr); return 2
    if a.command=='harness-verify' and result['comparison_status']!='MATCH':return 1
    if a.command=='env-check' and result['status']!='PASS':return 1
    return 0
if __name__=='__main__': sys.exit(main())
