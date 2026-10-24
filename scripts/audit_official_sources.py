#!/usr/bin/env python3
"""V10 official-site monitor: cautious manual audit, no public claims or alerts.

Reads the editorial directory, checks robots.txt, and fetches permitted HTML
homepages at a modest rate. Reports status only; page changes are NOT treated
as ticket releases, dates, or line-up announcements.
"""
import json
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

ROOT=pathlib.Path(__file__).resolve().parents[1]
directory=json.loads((ROOT/"data/festival-directory.json").read_text(encoding="utf-8"))
output=[]
agent="FestivalRadarResearchBot"
for item in directory["festivals"]:
    url=item["officialWebsite"]
    row={"id":item["id"],"officialWebsite":url,"status":"not_checked"}
    try:
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!="https" or not parsed.hostname:
            row["status"]="invalid_url"
        else:
            robots_url=urllib.parse.urlunsplit((parsed.scheme,parsed.netloc,"/robots.txt","",""))
            robots=urllib.robotparser.RobotFileParser()
            robots.set_url(robots_url)
            try:
                robots.read()
                allowed=robots.can_fetch(agent,url)
            except Exception:
                allowed=False
            if not allowed:
                row["status"]="robots_disallowed_or_unavailable"
            else:
                request=urllib.request.Request(url,headers={"User-Agent":agent,"Accept":"text/html"})
                with urllib.request.urlopen(request,timeout=12) as response:
                    kind=response.headers.get("Content-Type","")
                    row["status"]="reachable_html" if "text/html" in kind else "non_html"
                    row["httpStatus"]=response.status
    except (urllib.error.URLError,TimeoutError,ValueError) as exc:
        row["status"]="unavailable"
    output.append(row)
    time.sleep(1)
report={"note":"Manual connectivity and robots audit only; no festival announcements verified.", "results":output}
dest=ROOT/"data/official-source-audit.json"
dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
for r in output: print(r["id"],r["status"])
print("No alerts or emails sent.")
