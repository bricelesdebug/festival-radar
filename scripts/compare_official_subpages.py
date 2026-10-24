#!/usr/bin/env python3
"""V15 manual, review-only comparison of permitted official subpage metadata.

Uses a curated URL allowlist, never auto-promotes discovered links.
Does not infer ticket sales or lineup announcements. No emails or DB writes.
"""
import datetime as dt
import hashlib
import html
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import urllib.robotparser

ROOT=Path(__file__).resolve().parents[1]
ALLOWLIST=ROOT/"data/official-pages-approved.json"
BASELINE=ROOT/"data/official-subpage-baseline.json"
REPORT=ROOT/"data/official-subpage-changes.json"
AGENT="FestivalRadarResearchBot"
approved=json.loads(ALLOWLIST.read_text(encoding="utf8")).get("pages",[])
previous=json.loads(BASELINE.read_text(encoding="utf8")) if BASELINE.exists() else {}
current=dict(previous)
changes=[]
def extract(pattern,body):
 m=re.search(pattern,body,re.I|re.S)
 return html.unescape(re.sub(r"\s+"," ",m.group(1)).strip())[:300] if m else ""
for page in approved:
 url=page.get("url","")
 parts=urllib.parse.urlsplit(url)
 if parts.scheme!="https" or not parts.hostname:
  print("Skipped invalid URL");continue
 rp=urllib.robotparser.RobotFileParser()
 rp.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
 try:rp.read();allowed=rp.can_fetch(AGENT,url)
 except Exception:allowed=False
 if not allowed:
  print(page.get("festival","source"),"robots unavailable/disallowed");continue
 try:
  req=urllib.request.Request(url,headers={"User-Agent":AGENT,"Accept":"text/html"})
  with urllib.request.urlopen(req,timeout=15) as res:
   if "text/html" not in res.headers.get("Content-Type",""):
    print("Non-HTML page skipped");continue
   body=res.read(200000).decode("utf8",errors="replace")
  title=extract(r"<title[^>]*>(.*?)</title>",body)
  if not title:continue
  desc=extract(r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',body)
  digest=hashlib.sha256((title+"\n"+desc).encode()).hexdigest()
  old=previous.get(url)
  if old and old.get("digest")!=digest:
   changes.append({"festival":page.get("festival"),"url":url,"topics":page.get("topics",[]),
                   "previousTitle":old.get("title"),"currentTitle":title,
                   "reviewRequired":True,"verifiedAnnouncement":False})
  current[url]={"digest":digest,"title":title,"description":desc}
  print(page.get("festival","source"),"checked")
 except Exception:
  print(page.get("festival","source"),"unavailable; keeping previous baseline")
BASELINE.write_text(json.dumps(current,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
REPORT.write_text(json.dumps({"checkedAt":dt.datetime.now(dt.timezone.utc).isoformat(),
 "changes":changes,"note":"Metadata changes only, NOT verified ticket/lineup/date announcements.",
 "notificationsEnabled":False},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("Approved pages:",len(approved),"review-only changes:",len(changes))
