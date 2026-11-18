"""Diagnostic only: does Finnhub /quote expose a trade timestamp in extended hours?
Does not modify Rose quotes.json, stock valuations, or API secrets.
"""
import os, json, time, datetime, urllib.parse, urllib.request, urllib.error
from zoneinfo import ZoneInfo

KEY = os.environ.get('FINNHUB_API_KEY', '').strip()
if not KEY:
    raise SystemExit('ERROR: FINNHUB_API_KEY GitHub secret missing')
ny = ZoneInfo('America/New_York')
now = datetime.datetime.now(ny)
print('Test time (New York):', now.isoformat())
print('Market phase based on local clock (not a market holiday calendar):',
      'pre-market' if datetime.time(4)<=now.time()<datetime.time(9,30) else
      'regular' if datetime.time(9,30)<=now.time()<datetime.time(16) else
      'after-hours' if datetime.time(16)<=now.time()<datetime.time(20) else 'closed')
print('WARNING: /quote does not label c as premarket or afterhours. A timestamp alone cannot certify session coverage.')
for sym in ['AAPL','NVDA','TSLA']:
    url='https://finnhub.io/api/v1/quote?'+urllib.parse.urlencode({'symbol':sym,'token':KEY})
    try:
        req=urllib.request.Request(url, headers={'User-Agent':'Rose-extended-hours-diagnostic/1.0'})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw=r.read().decode('utf-8')
        data=json.loads(raw)
        stamp=data.get('t')
        dt=datetime.datetime.fromtimestamp(stamp, ny).isoformat() if isinstance(stamp,(int,float)) and stamp>0 else 'none'
        print(json.dumps({'symbol':sym,'c':data.get('c'),'pc':data.get('pc'),'timestamp_ny':dt,
                          'note':'c is generic quote, NOT verified extended-hours trade'},ensure_ascii=False))
    except urllib.error.HTTPError as e:
        print(f'{sym}: HTTP {e.code}; possible quota/permission issue')
    except Exception as e:
        print(f'{sym}: {type(e).__name__}: {e}')
    time.sleep(1.5)
print('Compare results from a run during premarket (04:00-09:30 ET) and afterhours (16:00-20:00 ET).')
print('If c/t do not move during those sessions, /quote is insufficient. Even if they move, verify against an independent extended-hours source.')
