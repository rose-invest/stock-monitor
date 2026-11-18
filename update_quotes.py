#!/usr/bin/env python3
"""Finnhub -> quotes.json. Python stdlib only; secret supplied by GitHub Actions."""
import datetime as dt
import json
import os
from pathlib import Path
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
KEY=os.environ.get('FINNHUB_API_KEY','').strip()
if not KEY:
    sys.exit('FINNHUB_API_KEY is missing; configure Actions repository secret')
now=dt.datetime.now(dt.timezone.utc)
ny=now.astimezone(ZoneInfo('America/New_York'))
# Manual runs allowed anytime; scheduled runs restricted to US trading session weekdays.
manual=os.environ.get('MANUAL_RUN','false').lower()=='true'
if not manual and (ny.weekday()>=5 or not(dt.time(9,30)<=ny.time()<dt.time(16,15))):
    print('Outside regular US trading hours; skipping',ny.isoformat())
    sys.exit(0)
symbols=json.loads((ROOT/'symbols.json').read_text())
assert len(symbols)==len(set(symbols))
out=ROOT/'quotes.json'
try:
    old=json.loads(out.read_text()) if out.exists() else {}
except (ValueError,OSError):
    old={}
quotes=old.get('quotes',{}) if isinstance(old.get('quotes'),dict) else {}
updated=0
errors=[]
for i,symbol in enumerate(symbols,1):
    url='https://finnhub.io/api/v1/quote?'+urllib.parse.urlencode({'symbol':symbol})
    req=urllib.request.Request(url,headers={'X-Finnhub-Token':KEY,'User-Agent':'RoseStockMonitor/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=18) as response:
                payload=json.load(response)
            price=float(payload.get('c') or 0)
            timestamp=int(payload.get('t') or 0)
            if price>0 and timestamp>0 and timestamp*1000 <= int(time.time()*1000)+60000:
                previous=quotes.get(symbol,{})
                if timestamp*1000>=int(previous.get('t',0)):
                    quotes[symbol]={'p':price,'t':timestamp*1000}
                    updated+=1
            else:
                errors.append(f'{symbol}: empty quote')
            break
        except urllib.error.HTTPError as exc:
            if exc.code in (401,403):
                sys.exit(f'Finnhub authorization failed (HTTP {exc.code}); check API secret')
            if exc.code==429:
                if attempt==2:
                    errors.append(f'{symbol}: rate limited')
                else:
                    time.sleep(65)
            elif attempt==2:
                errors.append(f'{symbol}: HTTP {exc.code}')
            else:
                time.sleep(3)
        except (urllib.error.URLError,TimeoutError,ValueError) as exc:
            if attempt==2:
                errors.append(f'{symbol}: {type(exc).__name__}')
            else:
                time.sleep(3)
    if i<len(symbols):time.sleep(1.25+random.uniform(0,0.15))
# Persist only successful valid quotes, retaining last good data for failed symbols.
result={'version':1,'updated_at':now.isoformat(timespec='seconds'),'successful_this_run':updated,'total_symbols':len(symbols),'quotes':quotes}
out.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
print(f'Updated {updated}/{len(symbols)} symbols; cache has {len(quotes)}; errors={len(errors)}')
if errors:print('Sample errors:', '; '.join(errors[:12]))
if not quotes:
    sys.exit('No valid quotes received; check Finnhub plan, symbol support, and API key')
