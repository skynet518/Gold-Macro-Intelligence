"""Deterministic, dependency-free research calculations. No order routing."""
from datetime import datetime, timezone
from math import isfinite

MODULES = ('macro', 'cftc', 'etf_physical', 'central_banks', 'liquidity', 'options')
CATEGORIES = ('producer', 'swap_dealer', 'managed_money', 'other_reportable')

def timestamp(s):
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if d.tzinfo is None: raise ValueError('timestamps must include timezone')
    return d.astimezone(timezone.utc)

def number(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v):
        raise ValueError('expected finite number')
    return float(v)

def validate_observation(o):
    required = ('module','metric','value','unit','observed_at','published_at','retrieved_at','source','url','vintage')
    if any(k not in o or o[k] in ('', None) for k in required): raise ValueError('missing provenance field')
    if o['module'] not in MODULES: raise ValueError('unknown module')
    v=number(o['value'])
    if o['metric'] in ('long','short','gold_tonnes','etf_tonnes','put_call_ratio') and v < 0: raise ValueError('negative quantity')
    if not isinstance(o['source'], str) or not isinstance(o['url'], str) or not o['url'].startswith(('https://','synthetic://')): raise ValueError('invalid source or URL')
    obs, pub, ret = (timestamp(o[k]) for k in ('observed_at','published_at','retrieved_at'))
    if not obs <= pub <= ret: raise ValueError('invalid observation/publication/retrieval order')
    if o['module'] == 'central_banks' and not o.get('country'): raise ValueError('central bank observation requires country')
    return o

def asof(observations, when):
    """Latest published vintage per metric, period, dimensions, known by decision time."""
    t = timestamp(when); selected = {}
    for o in observations:
        validate_observation(o)
        # Retrieval proves availability to this workflow; avoids retroactive downloads masquerading as archives.
        if timestamp(o['published_at']) > t or timestamp(o['retrieved_at']) > t: continue
        key = (o['module'], o['metric'], o.get('country'), o.get('category'), o['observed_at'])
        prev = selected.get(key)
        if prev is None or (timestamp(o['published_at']), timestamp(o['retrieved_at'])) > (timestamp(prev['published_at']), timestamp(prev['retrieved_at'])): selected[key] = o
    return list(selected.values())

def latest(rows, metric, **dimensions):
    x = [o for o in rows if o['metric']==metric and all(o.get(k)==v for k,v in dimensions.items())]
    return max(x, key=lambda o: timestamp(o['observed_at'])) if x else None

def report(data):
    now=timestamp(data['as_of']); rows=asof(data['observations'],data['as_of'])
    age_limits=data.get('max_age_days',{})
    issues=[]; modules={}
    for mod in MODULES:
        rs=[x for x in rows if x['module']==mod]
        # Every latest metric and dimension must pass age gate, not just one fresh value.
        keys={(x['metric'],x.get('country'),x.get('category')) for x in rs}
        current=[latest(rs,m,**({'country':c} if c else {}),**({'category':cat} if cat else {})) for m,c,cat in sorted(keys, key=lambda k: tuple(v or '' for v in k))]
        stale=[x['metric'] for x in current if (now-timestamp(x['observed_at'])).total_seconds()/86400 > number(age_limits.get(mod, 0))]
        modules[mod]={'available':bool(rs), 'latest_observations':current, 'stale_metrics':stale}
        if not rs: issues.append('missing module: '+mod)
        if stale: issues.append('stale module: '+mod)
    # A module is complete only when its explicitly required fields are present and fresh.
    required={'macro':['real_yield_10y','usd_index'], 'cftc':['long','short'], 'etf_physical':['etf_tonnes'], 'central_banks':['gold_tonnes'], 'liquidity':['liquidity_proxy'], 'options':['put_call_ratio']}
    for mod, metrics in required.items():
        for metric in metrics:
            if not any(x['metric']==metric for x in modules[mod]['latest_observations']): issues.append('missing metric: '+mod+'.'+metric)
    cftc={}
    for category in CATEGORIES:
        l=latest([x for x in rows if x['module']=='cftc'],'long',category=category); s=latest([x for x in rows if x['module']=='cftc'],'short',category=category)
        if l and s and l['module']==s['module']=='cftc' and l['observed_at']==s['observed_at'] and l['unit']==s['unit']=='contracts':
            cftc[category]={'long':l['value'],'short':s['value'],'net':number(l['value'])-number(s['value'])}
        else: issues.append('missing or mismatched CFTC pair: '+category)
    countries={}
    for c in sorted({x['country'] for x in rows if x['module']=='central_banks'}):
        h=sorted([x for x in rows if x['module']=='central_banks' and x['metric']=='gold_tonnes' and x['country']==c],key=lambda x:timestamp(x['observed_at']))
        if h:
            curr=h[-1]; prev=h[-2] if len(h)>1 else None
            countries[c]={'latest_tonnes':curr['value'],'period':curr['observed_at'],'previous_change_tonnes':round(number(curr['value'])-number(prev['value']),6) if prev and curr['unit']==prev['unit']=='tonnes' else None,'caveat':'change in reported holdings is not necessarily purchases; verify reclassifications and revisions'}
    risk=data.get('risk',{})
    risk_keys=('portfolio_weight','max_gold_weight','loss_fraction','max_loss_fraction')
    try:
        if not all(k in risk for k in risk_keys): raise ValueError()
        w,cap,loss,stop=(number(risk[k]) for k in risk_keys)
        if not all(0 <= v <= 1 for v in (w,cap,loss,stop)) or cap==0 or stop==0: raise ValueError()
    except (ValueError,TypeError):
        issues.append('risk limits missing or invalid'); w=cap=loss=stop=None
    # No statistical weights or optimization: only predeclared qualitative research hypotheses.
    hypothesis=data.get('research_hypothesis','observe')
    if hypothesis not in ('bullish','neutral','bearish','observe'): raise ValueError('invalid research hypothesis')
    if issues: decision='数据不足'
    elif w >= cap or loss >= stop: decision='减仓候选' if w>0 else '观望'
    elif hypothesis=='bullish': decision='加仓候选'
    elif hypothesis=='bearish': decision='减仓候选' if w>0 else '观望'
    elif hypothesis=='neutral': decision='持有' if w>0 else '观望'
    else: decision='观望'
    return {'as_of':data['as_of'],'decision':decision,'decision_basis':'unvalidated user-supplied hypothesis and configured risk gates; not a tested model','issues':issues,'modules':modules,'cftc_categories':cftc,'central_banks':countries,'warnings':['Research only; no execution. No verified predictive weights.','CFTC categories describe positions, not trader identity or cash flows.','Central bank observations are delayed and may be revised.']}

def drawdowns(prices, threshold=0.1):
    """Non-overlapping high-watermark episodes, durations in calendar days, right censoring."""
    threshold=number(threshold)
    if not 0 < threshold < 1: raise ValueError('threshold must be between 0 and 1')
    p=[]
    for x in prices:
        dt=timestamp(x['at']); v=number(x['price'])
        if v<=0 or (p and dt<=p[-1][0]): raise ValueError('positive prices and strictly increasing timestamps required')
        p.append((dt,v))
    if not p: return []
    peak=p[0]; trough=peak; active=False; events=[]
    def event(end,recovered):
        return {'peak_at':peak[0].isoformat(),'trough_at':trough[0].isoformat(),'end_at':end[0].isoformat(),'drawdown':trough[1]/peak[1]-1,'fall_days':(trough[0]-peak[0]).total_seconds()/86400,'recovery_days_from_trough':(end[0]-trough[0]).total_seconds()/86400 if recovered else None,'duration_days_from_peak':(end[0]-peak[0]).total_seconds()/86400,'recovered':recovered,'right_censored':not recovered}
    for item in p[1:]:
        if item[1]>=peak[1]:
            if active: events.append(event(item,True))
            peak=trough=item; active=False
        else:
            if item[1]<trough[1]: trough=item
            if trough[1] <= peak[1]*(1-threshold): active=True
    if active: events.append(event(p[-1],False))
    return events

def survival(events):
    """Kaplan-Meier from peak to recovery, censored at last observation."""
    times=sorted({e['duration_days_from_peak'] for e in events}); n=len(events); s=1.; out=[]
    for t in times:
        d=sum(e['recovered'] for e in events if e['duration_days_from_peak']==t)
        c=sum(e['right_censored'] for e in events if e['duration_days_from_peak']==t)
        if n and d: s*=1-d/n
        out.append({'days':t,'at_risk':n,'recoveries':d,'censored':c,'unrecovered_probability':s})
        n-=d+c
    return out

def backtest(data):
    """Predeclared signals only, time split, next-bar entry, long/flat, one-way costs."""
    prices=data['prices']; split=timestamp(data['test_start']); cost=number(data.get('one_way_cost_bps',0))/10000
    if not 0<=cost<1: raise ValueError('invalid costs')
    drawdowns(prices)  # validate order and prices
    signals=data['signals']; bytime={}
    for s in signals:
        t=timestamp(s['at']); published=timestamp(s['available_at'])
        if published>t or s['position'] not in (0,1) or t in bytime: raise ValueError('invalid, duplicate or forward-looking signal')
        bytime[t]=s['position']
    # Signals available at bar i enter at next bar; earn subsequent close-to-close returns.
    pos=0; equity=1.; records=[]; pending=0
    for i in range(1,len(prices)):
        t0=timestamp(prices[i-1]['at']); t=timestamp(prices[i]['at'])
        if t < split: continue
        # Enter at this close from the previous close's signal; return is earned next interval.
        ret=number(prices[i]['price'])/number(prices[i-1]['price'])-1
        equity*=1+pos*ret
        target=bytime.get(t0, pos) if t0>=split else pos
        turnover=abs(target-pos); equity*=1-turnover*cost; pos=target
        records.append({'at':prices[i]['at'],'position_after_close':pos,'turnover':turnover,'equity':equity})
    return {'test_start':data['test_start'],'execution':'previous-bar signal enters at next close; earns returns after that close','initial_equity':1,'final_equity':equity,'total_return':equity-1,'observations':len(records),'records':records,'limitations':'predeclared signals, long/flat, no financing, tax, slippage beyond configured cost; no training or optimization'}

# v0.2 point-in-time validation and research layer; drawdowns/backtest remain unchanged.
from .research import validate_observation, asof, report


def conditional_drawdowns(prices, threshold=0.1):
    """First threshold crossing known at the time; subsequent recovery is censored."""
    drawdowns(prices,threshold)  # shared validation
    if not prices: return []
    pts=[(timestamp(p['at']),number(p['price'])) for p in prices]
    peak=pts[0]; trigger=None; result=[]
    for t,v in pts[1:]:
        if v>=peak[1]:
            if trigger is not None: result.append({'peak_at':peak[0].isoformat(),'trigger_at':trigger.isoformat(),'end_at':t.isoformat(),'elapsed_days_from_trigger':(t-trigger).total_seconds()/86400,'recovered':True,'right_censored':False})
            peak=(t,v); trigger=None
        elif trigger is None and v<=peak[1]*(1-threshold): trigger=t
    if trigger is not None:
        t=pts[-1][0]; result.append({'peak_at':peak[0].isoformat(),'trigger_at':trigger.isoformat(),'end_at':t.isoformat(),'elapsed_days_from_trigger':(t-trigger).total_seconds()/86400,'recovered':False,'right_censored':True})
    return result
