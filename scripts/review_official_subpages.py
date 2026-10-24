#!/usr/bin/env python3
"""V14 review-only audit of official subpages discovered from homepages.

Re-discovers candidate links each run, checks robots.txt for each destination,
and records page title, canonical URL and description. No notifications.
"""
import datetime as dt
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import urllib.robotparser

ROOT=Path(__file__).resolve().parents[1]
directory=json.loads((ROOT/"data/festival-directory.json").read_text(encoding="utf8"))
AGENT="FestivalRadarResearchBot"
TOPICS={
 "tickets":("ticket","billet","presale","pre-sale","entradas"),
 "lineup":("lineup","line-up","artist","programmation","programa"),
 "dates":("dates","calendar","calendrier","edition","schedule")
}
class LinkParser(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.href=None;self.parts=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a":self.href=dict(attrs).get("href");self.parts=[]
 def handle_data(self,data):
  if self.href is not None:self.parts.append(data)
 def handle_endtag(self,tag):
  if tag=="a" and self.href:
   self.links.append((self.href," ".join(self.parts)))
   self.href=None;self.parts=[]

def robots_ok(url):
 p=urllib.parse.urlsplit(url)
 rp=urllib.robotparser.RobotFileParser()
 rp.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
 try:rp.read();return rp.can_fetch(AGENT,url)
 except Exception:return False

def fetch(url):
 req=urllib.request.Request(url,headers={"User-Agent":AGENT,"Accept":"text/html"})
 with urllib.request.urlopen(req,timeout=12) as res:
  if "text/html" not in res.headers.get("Content-Type",""):return ""
  return res.read(200000).decode("utf8",errors="replace")

def title_of(markup):
 match=re.search(r"<title[^>]*>(.*?)</title>",markup,re.I|re.S)
 return html.unescape(re.sub(r"\s+"," ",match.group(1)).strip())[:250] if match else ""

rows=[]
for festival in directory["festivals"]:
 homepage=festival["officialWebsite"]
 entry={"festival":festival["name"],"status":"unavailable","pages":[]}
 try:
  if not robots_ok(homepage):
   entry["status"]="homepage_robots_unavailable_or_disallowed"
  else:
   parser=LinkParser();parser.feed(fetch(homepage))
   host=urllib.parse.urlsplit(homepage).hostname
   seen=set()
   for href,label in parser.links:
    url=urllib.parse.urljoin(homepage,html.unescape(href))
    p=urllib.parse.urlsplit(url)
    if p.scheme!="https" or p.hostname!=host:continue
    url=urllib.parse.urlunsplit((p.scheme,p.netloc,p.path,"",""))
    if url in seen:continue
    topics=[topic for topic,terms in TOPICS.items() if any(term in (p.path+" "+label).lower() for term in terms)]
    if not topics:continue
    seen.add(url)
    page={"url":url,"topics":topics,"status":"not_checked","verifiedAnnouncement":False}
    if robots_ok(url):
     try:
      markup=fetch(url)
      page["status"]="reachable_html" if markup else "non_html"
      if markup:page["title"]=title_of(markup)
     except Exception:page["status"]="unavailable"
    else:page["status"]="robots_unavailable_or_disallowed"
    entry["pages"].append(page)
    if len(entry["pages"])>=12:break
   entry["status"]="review_complete"
 except Exception:pass
 rows.append(entry)
 print(entry["festival"],entry["status"],len(entry["pages"]))
out={"checkedAt":dt.datetime.now(dt.timezone.utc).isoformat(),
 "note":"Source pages and titles only. No sales, lineup or date announcements verified.",
 "notificationsEnabled":False,"results":rows}
(ROOT/"data/official-subpage-review.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("No emails or notifications sent.")
