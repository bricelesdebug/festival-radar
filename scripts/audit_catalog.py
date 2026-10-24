#!/usr/bin/env python3
"""Audit Ticketmaster discovery results before expanding Festival Radar coverage.

Read-only: writes a report under /tmp, not the public dataset. The current
collector's electronic classification and festival-name heuristics are imperfect.
"""
import json
import sys
from collections import Counter
from pathlib import Path

path=Path(sys.argv[1] if len(sys.argv)>1 else "data/festivals.json")
data=json.loads(path.read_text(encoding="utf-8"))
events=data.get("events", [])
if not isinstance(events,list):
    raise SystemExit("Invalid dataset: events must be a list")
ids=set()
duplicates=[]
missing=[]
genre_counts=Counter()
countries=Counter()
for i,e in enumerate(events):
    if not isinstance(e,dict):
        missing.append(i)
        continue
    eid=e.get("id")
    if not eid or not e.get("name") or not e.get("url") or not e.get("date"):
        missing.append(i)
    if eid in ids:
        duplicates.append(eid)
    ids.add(eid)
    countries[e.get("countryCode") or "unknown"]+=1
    for g in e.get("genres") or []:
        genre_counts[g]+=1
print("Festival Radar catalog audit")
print("Events:",len(events))
print("Countries:",dict(sorted(countries.items())))
print("Genres:",dict(sorted(genre_counts.items())))
print("Missing critical fields:",len(missing))
print("Duplicate IDs:",len(duplicates))
print("Warning: the API electronic category is broader than techno/house/electro.")
print("Warning: the presence of festival/fest/open-air in an event title does not confirm it is a festival.")
if missing or duplicates:
    raise SystemExit("Catalog audit failed: invalid or duplicate records")
