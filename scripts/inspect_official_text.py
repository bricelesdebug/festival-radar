#!/usr/bin/env python3
"""V17: inspect visible text of approved official pages for manual selector design.

Respect robots.txt. Extract only headings, button labels and short text samples;
no automated sale claims, user alerts or database writes.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
import json
import re

ROOT=Path(__file__).resolve().parents[1]
pages=json.loads((ROOT/"data/official-pages-approved.json").read_text(encoding="utf-8"))["pages"]
AGENT="FestivalRadarResearchBot"
WORDS=re.compile(r"ticket|sale|presale|sold.out|billet|line.up|artist|date|202[6-9]|202[0-9]|programm|available",re.I)
class Visible(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.tagstack=[];self.text=[];self.heading=[]
 def handle_starttag(self,tag,attrs):
  self.tagstack.append(tag)
  if tag in ("script","style","noscript","svg"):self.skip+=1
 def handle_endtag(self,tag):
  if tag in ("script","style","noscript","svg") and self.skip:self.skip-=1
  if self.tagstack:self.tagstack.pop()
 def handle_data(self,data):
  if self.skip:return
  clean=" ".join(data.split())
  if len(clean)<4:return
  if self.tagstack and self.tagstack[-1] in ("h1","h2","h3","h4","button"):
   self.heading.append(clean[:160])
  if WORDS.search(clean):self.text.append(clean[:220])
results=[]
for page in pages:
 url=page["url"];parts=urlsplit(url)
 row={"festival":page["festival"],"url":url,"topics":page.get("topics",[]),"status":"unavailable","headings":[],"candidateText":[],"verifiedAnnouncement":False}
 rp=RobotFileParser();rp.set_url(f"{parts.scheme}://{parts.netloc}/robots.txt")
 try:rp.read();allowed=rp.can_fetch(AGENT,url)
 except Exception:allowed=False
 if not allowed:
  row["status"]="robots_disallowed_or_unavailable"
 else:
  try:
   with urlopen(Request(url,headers={"User-Agent":AGENT,"Accept":"text/html"}),timeout=15) as response:
    if "text/html" not in response.headers.get("Content-Type",""):
     row["status"]="non_html"
    else:
     html=response.read(250000).decode("utf-8",errors="replace")
     parser=Visible();parser.feed(html)
     row["status"]="ok";row["headings"]=list(dict.fromkeys(parser.heading))[:25]
     row["candidateText"]=list(dict.fromkeys(parser.text))[:35]
  except Exception:pass
 results.append(row)
 print(row["festival"],row["status"],len(row["headings"]),"headings",len(row["candidateText"]),"text candidates")
output={"note":"Unverified visible-text samples for selector development; no ticket-sale claims.","notificationsEnabled":False,"results":results}
(ROOT/"data/official-visible-text-review.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("No notifications or emails sent.")
