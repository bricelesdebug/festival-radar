#!/usr/bin/env python3
"""V13: discover candidate official subpages for human review.

Only follows same-host links found on permitted official homepages.
Does not fetch discovered pages or claim any announcement is verified.
No user notifications, emails, or Supabase writes.
"""
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.robotparser

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/"data/festival-directory.json").read_text(encoding="utf-8"))
AGENT="FestivalRadarResearchBot"
WORDS={
    "tickets":("ticket","billet","presale","pre-sale","entradas","tickets"),
    "lineup":("lineup","line-up","artists","artistes","programme","programacion","programmation"),
    "dates":("dates","calendar","calendrier","edition","schedule"),
}
class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.href=None;self.label=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.href=dict(attrs).get("href");self.label=[]
    def handle_data(self,data):
        if self.href is not None:self.label.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.href:
            self.links.append((self.href," ".join(self.label).strip()))
            self.href=None;self.label=[]

def allowed(url):
    p=urllib.parse.urlsplit(url)
    robots=urllib.robotparser.RobotFileParser()
    robots.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
    try:
        robots.read()
        return robots.can_fetch(AGENT,url)
    except Exception:
        return False

report=[]
for item in DATA["festivals"]:
    url=item["officialWebsite"]
    p=urllib.parse.urlsplit(url)
    record={"festival":item["name"],"homepage":url,"status":"not_checked","candidates":[]}
    if p.scheme!="https" or not p.hostname or not allowed(url):
        record["status"]="robots_disallowed_or_unavailable"
        report.append(record);continue
    try:
        req=urllib.request.Request(url,headers={"User-Agent":AGENT,"Accept":"text/html"})
        with urllib.request.urlopen(req,timeout=12) as resp:
            if "text/html" not in resp.headers.get("Content-Type",""):
                record["status"]="non_html";report.append(record);continue
            markup=resp.read(250000).decode("utf-8",errors="replace")
        parser=Links();parser.feed(markup)
        seen=set()
        for href,label in parser.links:
            absolute=urllib.parse.urljoin(url,html.unescape(href))
            dest=urllib.parse.urlsplit(absolute)
            if dest.scheme!="https" or dest.hostname!=p.hostname:continue
            canonical=urllib.parse.urlunsplit((dest.scheme,dest.netloc,dest.path,"",""))
            if canonical in seen:continue
            text=(dest.path+" "+label).lower()
            categories=[category for category,words in WORDS.items() if any(word in text for word in words)]
            if categories:
                seen.add(canonical)
                record["candidates"].append({"url":canonical,"topics":categories,"linkText":label[:120],
                    "reviewRequired":True,"verifiedAnnouncement":False})
            if len(record["candidates"])>=30:break
        record["status"]="ok"
    except Exception:
        record["status"]="unavailable"
    report.append(record)
    print(item["name"],record["status"],len(record["candidates"]))
output={"note":"Candidate links only. Not validated announcements or confirmed permitted subpage crawls.",
        "results":report,"notificationsEnabled":False}
dest=ROOT/"data/official-page-candidates.json"
dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("No alerts or emails sent.")
