#!/usr/bin/env python3
"""Extract potential Event structured data from approved festival pages.

Read-only, review-only. JSON-LD claims are not independently verified.
No email, notification or Supabase access.
"""
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

ROOT=Path(__file__).resolve().parents[1]
PAGES=json.loads((ROOT/"data/official-pages-approved.json").read_text(encoding="utf-8"))["pages"]
AGENT="FestivalRadarResearchBot"
class Scripts(HTMLParser):
    def __init__(self): super().__init__();self.capture=False;self.parts=[];self.scripts=[]
    def handle_starttag(self,tag,attrs):
        if tag=="script" and "ld+json" in dict(attrs).get("type","").lower():
            self.capture=True;self.parts=[]
    def handle_data(self,data):
        if self.capture:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="script" and self.capture:
            self.scripts.append("".join(self.parts));self.capture=False
def walk(node):
    if isinstance(node,list):
        for n in node:yield from walk(n)
    elif isinstance(node,dict):
        if "@graph" in node:yield from walk(node["@graph"])
        kinds=node.get("@type",[])
        if isinstance(kinds,str):kinds=[kinds]
        if any(k=="Event" or k.endswith("/Event") or k.endswith("#Event") for k in kinds):
            yield node
def summarize(ev):
    offers=ev.get("offers")
    if isinstance(offers,list):offers=offers[0] if offers else {}
    if not isinstance(offers,dict):offers={}
    location=ev.get("location")
    if isinstance(location,list):location=location[0] if location else {}
    if not isinstance(location,dict):location={}
    return {k:v for k,v in {
        "name":ev.get("name"),"startDate":ev.get("startDate"),
        "endDate":ev.get("endDate"),"eventStatus":ev.get("eventStatus"),
        "locationName":location.get("name"),"offerAvailability":offers.get("availability"),
        "offerUrl":offers.get("url")
    }.items() if isinstance(v,str)}
report=[]
for page in PAGES:
    url=page["url"];p=urlsplit(url)
    entry={"festival":page["festival"],"source":url,"topics":page.get("topics",[]),
           "status":"not_checked","events":[],"reviewRequired":True}
    if p.scheme!="https" or not p.hostname:
        entry["status"]="invalid_url";report.append(entry);continue
    robots=RobotFileParser()
    robots.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
    try:robots.read();permitted=robots.can_fetch(AGENT,url)
    except Exception:permitted=False
    if not permitted:
        entry["status"]="robots_unavailable_or_disallowed";report.append(entry);continue
    try:
        req=Request(url,headers={"User-Agent":AGENT,"Accept":"text/html"})
        with urlopen(req,timeout=15) as response:
            if "text/html" not in response.headers.get("Content-Type",""):
                entry["status"]="non_html";report.append(entry);continue
            markup=response.read(250000).decode("utf-8",errors="replace")
        parser=Scripts();parser.feed(markup)
        for block in parser.scripts[:20]:
            try:
                for event in walk(json.loads(block)):
                    entry["events"].append(summarize(event))
                    if len(entry["events"])>=20:break
            except (ValueError,TypeError):continue
        entry["status"]="ok"
    except Exception:
        entry["status"]="unavailable"
    report.append(entry)
    print(entry["festival"],entry["status"],len(entry["events"]),"structured event(s)")
out={"note":"Source-provided structured metadata; NOT confirmed ticket release or verified lineup.",
     "verifiedAnnouncements":0,"notificationsEnabled":False,"results":report}
(ROOT/"data/official-structured-candidates.json").write_text(
    json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("No notifications or emails sent.")
