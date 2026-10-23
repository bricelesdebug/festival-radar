#!/usr/bin/env python3
"""Ticketmaster Discovery API collector; requires TICKETMASTER_API_KEY."""
import datetime as dt, json, os, pathlib, time, urllib.parse, urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
KEY=os.getenv('TICKETMASTER_API_KEY')
if not KEY: raise SystemExit('Missing TICKETMASTER_API_KEY; refusing to overwrite existing data')
COUNTRIES={'BE':'Belgique','NL':'Pays-Bas','FR':'France','DE':'Allemagne','ES':'Espagne','IT':'Italie','PT':'Portugal','GB':'Royaume-Uni','CH':'Suisse','AT':'Autriche','PL':'Pologne','CZ':'Tchéquie','HR':'Croatie','HU':'Hongrie','DK':'Danemark','SE':'Suède'}
terms=('festival','fest','open air','open-air')
now=dt.datetime.now(dt.timezone.utc)
records={}
for code,country in COUNTRIES.items():
 for page in range(2):
  params={'apikey':KEY,'countryCode':code,'classificationName':'Electronic','size':100,'page':page,'sort':'date,asc','startDateTime':now.strftime('%Y-%m-%dT%H:%M:%SZ')}
  url='https://app.ticketmaster.com/discovery/v2/events.json?'+urllib.parse.urlencode(params)
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'FestivalRadar/0.2 (event discovery)'})
   with urllib.request.urlopen(req,timeout=25) as res: payload=json.load(res)
  except Exception as exc:
   print(f'WARN {code} page {page}: {exc}')
   break
  events=payload.get('_embedded',{}).get('events',[])
  for e in events:
   name=e.get('name','')
   if not any(term in name.lower() for term in terms): continue
   eid=e.get('id'); link=e.get('url')
   if not eid or not link: continue
   venue=(e.get('_embedded',{}).get('venues') or [{}])[0]
   sale=e.get('sales',{}).get('public',{})
   classifications=e.get('classifications') or []
   genres=sorted(set(x.get('genre',{}).get('name','') for x in classifications if x.get('genre',{}).get('name')))
   records[eid]={'id':eid,'name':name,'city':venue.get('city',{}).get('name',''),'country':country,'countryCode':code,'date':e.get('dates',{}).get('start',{}).get('localDate'),'url':link,'source':'Ticketmaster Discovery API','genres':genres,'salesStart':sale.get('startDateTime'),'salesEnd':sale.get('endDateTime'),'saleStatus':'on_sale' if sale.get('startDateTime') and sale['startDateTime']<=now.isoformat().replace('+00:00','Z') and (not sale.get('endDateTime') or sale['endDateTime']>now.isoformat().replace('+00:00','Z')) else 'unverified'}
  if len(events)<100: break
  time.sleep(.25)
print(f'Collected {len(records)} festival-like events')
if not records: raise SystemExit('No records found; preserving existing dataset')
output={'updatedAt':now.isoformat(),'source':'Ticketmaster Discovery API','note':'Discovery API data; not independently verified. Festival classification is heuristic.','events':sorted(records.values(),key=lambda e:(e['date'] or '9999',e['name']))}
path=ROOT/'data'/'festivals.json'; path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Saved',path)
