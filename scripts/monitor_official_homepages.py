#!/usr/bin/env python3
"""V11: review-only homepage change monitoring for two official festivals.

Respects robots.txt, fetches a bounded HTML response, extracts title and
meta description only, and compares with the previous committed baseline.
No alerts, no inferred ticket-sale or lineup announcements.
"""
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

ROOT=pathlib.Path(__file__).resolve().parents[1]
BASELINE=ROOT/"data"/"official-homepage-baseline.json"
REPORT=ROOT/"data"/"official-homepage-changes.json"
TARGETS={
    "tomorrowland":"https://www.tomorrowland.com/",
    "awakenings-festival":"https://www.awakenings.com/",
}
AGENT="FestivalRadarResearchBot"
previous=json.loads(BASELINE.read_text(encoding="utf8")) if BASELINE.exists() else {}
now=dt.datetime.now(dt.timezone.utc).isoformat()
current={}
changes=[]
def extract(pattern,content):
    match=re.search(pattern,content,re.I|re.S)
    return html.unescape(re.sub(r"\s+"," ",match.group(1)).strip())[:300] if match else ""

for name,url in TARGETS.items():
    result={"url":url,"checkedAt":now,"status":"unavailable"}
    try:
        parts=urllib.parse.urlsplit(url)
        robots_url=f"{parts.scheme}://{parts.netloc}/robots.txt"
        robots=urllib.robotparser.RobotFileParser()
        robots.set_url(robots_url)
        try:
            robots.read()
            allowed=robots.can_fetch(AGENT,url)
        except Exception:
            allowed=False
        if not allowed:
            result["status"]="robots_unavailable_or_disallowed"
        else:
            req=urllib.request.Request(url,headers={"User-Agent":AGENT,"Accept":"text/html"})
            with urllib.request.urlopen(req,timeout=15) as resp:
                content_type=resp.headers.get("Content-Type","")
                if "text/html" not in content_type:
                    result["status"]="non_html"
                else:
                    body=resp.read(250000).decode("utf8",errors="replace")
                    title=extract(r"<title[^>]*>(.*?)</title>",body)
                    description=extract(r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',body)
                    if not title:
                        result["status"]="missing_title"
                    else:
                        result.update(status="ok",title=title,description=description,
                            digest=hashlib.sha256((title+"\n"+description).encode()).hexdigest())
    except (urllib.error.URLError,TimeoutError,ValueError):
        pass
    old=previous.get(name)
    if result["status"]=="ok":
        current[name]=result
        if old and old.get("digest")!=result["digest"]:
            changes.append({"festival":name,"kind":"homepage_metadata_changed",
                            "oldTitle":old.get("title"),"newTitle":result["title"],
                            "source":url,"reviewRequired":True})
    elif old:
        current[name]=old
    print(name,result["status"])
REPORT.write_text(json.dumps({"checkedAt":now,"changes":changes,
  "note":"Metadata changes are NOT verified announcements; no notifications sent."},
  ensure_ascii=False,indent=2)+"\n",encoding="utf8")
BASELINE.write_text(json.dumps(current,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("Review-only metadata changes:",len(changes))
