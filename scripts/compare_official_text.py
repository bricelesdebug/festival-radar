#!/usr/bin/env python3
"""V18: compare reviewed visible-text extracts against the last baseline.

Run AFTER inspect_official_text.py. A changed text excerpt is a review
candidate, never a confirmed sale or lineup announcement.
No network access, emails, Supabase writes, or user notifications.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/"data/official-visible-text-review.json"
baseline=ROOT/"data/official-text-baseline.json"
report=ROOT/"data/official-text-changes.json"
data=json.loads(source.read_text(encoding="utf-8"))
old=json.loads(baseline.read_text(encoding="utf-8")) if baseline.exists() else {}
new=dict(old)
changes=[]
checked=0
for row in data.get("results",[]):
    if row.get("status")!="ok":
        continue  # A failed fetch must not erase a good baseline.
    url=row.get("url")
    if not url:continue
    checked+=1
    # Normalize whitespace and order; no arbitrary page markup or scripts.
    texts=sorted(set(" ".join(t.split()) for t in row.get("candidateText",[]) if t.strip()))
    digest=hashlib.sha256(json.dumps(texts,ensure_ascii=False).encode()).hexdigest()
    previous=old.get(url)
    if previous and previous.get("digest")!=digest:
        before=set(previous.get("texts",[]))
        additions=[t for t in texts if t not in before]
        if additions:
            changes.append({
                "festival":row.get("festival"),"source":url,
                "topics":row.get("topics",[]),
                "newTextCandidates":additions[:15],
                "reviewRequired":True,"verifiedAnnouncement":False
            })
    new[url]={"digest":digest,"texts":texts}
baseline.write_text(json.dumps(new,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
report.write_text(json.dumps({
    "checkedAt":dt.datetime.now(dt.timezone.utc).isoformat(),
    "checkedPages":checked,
    "changes":changes,
    "note":"Text additions are unverified review candidates, NOT ticket-release confirmations.",
    "notificationsEnabled":False
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(f"Compared {checked} pages; {len(changes)} review candidates; no notifications.")
