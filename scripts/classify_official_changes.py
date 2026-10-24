#!/usr/bin/env python3
"""V12: classify changed official homepage metadata for human review only.

This is NOT proof of a ticket sale, lineup or date announcement.
No network calls, email, Supabase writes or user notifications.
"""
import json
import pathlib
import re

ROOT=pathlib.Path(__file__).resolve().parents[1]
source=ROOT/"data/official-homepage-changes.json"
dest=ROOT/"data/official-announcement-candidates.json"
data=json.loads(source.read_text(encoding="utf-8"))
patterns={
    "tickets": r"\b(ticket|tickets|billet|billetterie|presale|pre-sale|on sale|voorverkoop|entradas)\b",
    "lineup": r"\b(line[ -]?up|artists?|artistes?|programmation|programa|affiche)\b",
    "dates": r"\b(dates?|calendar|calendrier|datum|fecha|edition|édition)\b",
}
results=[]
for change in data.get("changes",[]):
    if change.get("kind")!="homepage_metadata_changed":
        continue
    title=change.get("newTitle") or ""
    tags=[name for name,pat in patterns.items() if re.search(pat,title,re.I)]
    results.append({
        "festival":change.get("festival"),
        "source":change.get("source"),
        "headline":title[:300],
        "potentialTopics":tags,
        "reviewRequired":True,
        "verifiedAnnouncement":False,
        "confidence":"unverified_metadata_change",
    })
dest.write_text(json.dumps({
    "checkedAt":data.get("checkedAt"),
    "note":"Candidate topics based on homepage title changes only; NOT confirmed announcements.",
    "notificationsEnabled":False,
    "candidates":results
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("V12 review candidates:",len(results))
print("No notifications, emails, or database changes.")
