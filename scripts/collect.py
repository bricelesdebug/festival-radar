#!/usr/bin/env python3
"""Collect European discovery candidates atomically; never publish partial runs."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
COUNTRIES = {'BE':'Belgique','NL':'Pays-Bas','FR':'France','DE':'Allemagne',
             'ES':'Espagne','IT':'Italie','PT':'Portugal','GB':'Royaume-Uni',
             'CH':'Suisse','AT':'Autriche','PL':'Pologne','CZ':'Tchéquie',
             'HR':'Croatie','HU':'Hongrie','DK':'Danemark','SE':'Suède',
             'IE':'Irlande','NO':'Norvège','FI':'Finlande','EE':'Estonie',
             'LV':'Lettonie','LT':'Lituanie','RO':'Roumanie','GR':'Grèce'}
PAGE_SIZE = 100
MAX_PAGES = 10  # Discovery supports size * page < 1000.


def fetch_page(params):
    url = 'https://app.ticketmaster.com/discovery/v2/events.json?' + urllib.parse.urlencode(params)
    for attempt in range(3):
        time.sleep(.55)  # Below even a two requests/second quota.
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'FestivalRadar/0.3'})
            with urllib.request.urlopen(req, timeout=25) as response:
                payload = json.load(response)
            if not isinstance(payload, dict) or 'errors' in payload or 'fault' in payload:
                raise ValueError('Invalid API response')
            return payload
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f'API HTTP {exc.code}') from None
        except (OSError, ValueError):
            if attempt == 2:
                raise RuntimeError('API unavailable or invalid JSON') from None
        time.sleep(2 ** attempt)
    raise RuntimeError('Retry budget exhausted')


def normalize(event, code):
    name = event.get('name', '')
    if not re.search(r'festival|\bfest\b|\bopen[ -]air\b', name, re.I):
        return None
    classifications = event.get('classifications') or []
    genres = sorted({c.get(k, {}).get('name') for c in classifications
                     for k in ('genre', 'subGenre') if c.get(k, {}).get('name')})
    if not any('electronic' in g.lower() for g in genres):
        return None
    start = event.get('dates', {}).get('start', {})
    date = start.get('localDate')
    if start.get('dateTBA') or start.get('dateTBD'):
        date = None
    if not event.get('id') or not date:
        return None
    try:
        dt.date.fromisoformat(date)
        link = urllib.parse.urlsplit(event.get('url', ''))
        if link.scheme != 'https' or not link.hostname or link.username or link.password:
            return None
    except (ValueError, TypeError):
        return None
    venue = (event.get('_embedded', {}).get('venues') or [{}])[0]
    if venue.get('country', {}).get('countryCode', code) != code:
        return None
    sale = event.get('sales', {}).get('public', {})
    return {'id':str(event['id']), 'name':name, 'city':venue.get('city', {}).get('name', ''),
            'country':COUNTRIES[code], 'countryCode':code, 'date':date,
            'url':event['url'], 'source':'Ticketmaster Discovery API', 'genres':genres,
            'genreScope':'electronic_broad', 'festivalConfidence':'unverified',
            'salesStart':sale.get('startDateTime'), 'salesEnd':sale.get('endDateTime'),
            'eventStatus':event.get('dates', {}).get('status', {}).get('code', 'unknown'),
            'saleStatus':'unverified'}  # A sale window is not ticket availability.


def collect(key, now, fetch=fetch_page):
    records, coverage, failures = {}, {}, []
    for code in COUNTRIES:
        count = 0
        try:
            for page in range(MAX_PAGES):
                payload = fetch({'apikey':key, 'countryCode':code,
                                 'classificationName':'Electronic', 'size':PAGE_SIZE,
                                 'page':page, 'sort':'date,asc',
                                 'startDateTime':now.strftime('%Y-%m-%dT%H:%M:%SZ')})
                events = payload.get('_embedded', {}).get('events', [])
                if not isinstance(events, list):
                    raise ValueError('Invalid event list')
                count += len(events)
                for event in events:
                    record = normalize(event, code)
                    if record:
                        records[record['id']] = record
                total_pages = payload.get('page', {}).get('totalPages')
                if (isinstance(total_pages, int) and page + 1 >= total_pages) or len(events) < PAGE_SIZE:
                    break
                if page == MAX_PAGES - 1:
                    raise ValueError('Paging limit reached; coverage truncated')
            coverage[code] = {'status':'complete', 'scanned':count}
        except (RuntimeError, ValueError, TypeError, AttributeError):
            # Never log request URLs or exceptions that may contain the API key.
            coverage[code] = {'status':'failed', 'scanned':count}
            failures.append(code)
    report = {'updatedAt':now.isoformat(), 'complete':not failures,
              'countries':coverage, 'failedCountries':failures, 'candidateCount':len(records)}
    return records, report


def publish(records, report, output):
    if not report['complete'] or not records:
        raise ValueError('Incomplete or empty collection; existing catalog preserved')
    data = {'updatedAt':report['updatedAt'], 'source':'Ticketmaster Discovery API',
            'collection':report,
            'note':'Discovery candidates only; festival identity and ticket availability require review.',
            'events':sorted(records.values(), key=lambda e:(e['date'], e['name']))}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'data/festivals.json')
    parser.add_argument('--report', type=Path, default=Path('/tmp/festival-radar-collection-report.json'))
    args = parser.parse_args()
    key = os.getenv('TICKETMASTER_API_KEY')
    if not key:
        raise SystemExit('Missing TICKETMASTER_API_KEY; catalog preserved')
    records, report = collect(key, dt.datetime.now(dt.timezone.utc))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    try:
        publish(records, report, args.output)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    print(f'Saved {len(records)} candidates across {len(COUNTRIES)} country queries; no announcements sent.')


if __name__ == '__main__':
    main()
