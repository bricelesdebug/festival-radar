#!/usr/bin/env python3
"""Stage internal inbox notifications for favorited Ticketmaster events.

Server-only. Reads a review-only candidate JSON file; no email delivery.
Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in server secrets.
Only users who explicitly follow the event get an inbox entry.
"""
import json
import argparse
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from preview_alerts import matches

parser = argparse.ArgumentParser()
parser.add_argument("candidates")
parser.add_argument("--apply", action="store_true", help="Requires separate operator approval and reviewed keys")
args = parser.parse_args()
data = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
changes = data.get("changes", [])
if not isinstance(changes, list):
    raise SystemExit("Invalid candidate file")
if not args.apply:
    print(f"Preview only: {len(changes)} candidates need review. No database writes or emails.")
    raise SystemExit(0)
if os.environ.get("INBOX_WRITES_APPROVED") != "true":
    raise SystemExit("Inbox writes require explicit operator approval")
approved = data.get("reviewedEventKeys", [])
if not isinstance(approved, list) or not approved:
    raise SystemExit("Explicit reviewedEventKeys required")
changes = [c for c in changes if c.get("event_key") in approved]
if len(changes) > 100:
    raise SystemExit("Safety limit: over 100 changes")
BASE = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
if not BASE.startswith("https://") or not KEY:
    raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

def request(method, table, params="", payload=None, prefer=None):
    url = BASE + "/rest/v1/" + table + (("?" + params) if params else "")
    headers = {"apikey": KEY, "Authorization": "Bearer " + KEY,
               "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            content = resp.read()
            return json.loads(content) if content else []
    except urllib.error.HTTPError as exc:
        # Do not print headers, secrets or full response bodies.
        raise RuntimeError(f"Supabase {table} returned HTTP {exc.code}") from None

count = 0
processed = 0
for change in changes:
    processed += 1
    if processed > 100:
        raise SystemExit("Safety limit: over 100 changes; manual review required")
    key = change.get("event_key")
    fid = change.get("festival_id")
    if not key or not fid or change.get("event_type") not in (
            "new_event", "sales_start_changed", "event_date_changed"):
        continue
    # Upsert idempotently: re-running the same detection cannot create duplicate events.
    request("POST", "alert_events", "on_conflict=event_key", [{
        "event_key": key, "festival_id": fid,
        "event_type": change["event_type"], "payload": change.get("payload", {})
    }], "resolution=ignore-duplicates,return=minimal")
    users = request("GET", "favorites",
                    "select=user_id&festival_id=eq." + urllib.parse.quote(str(fid), safe=""))
    if not users:
        continue
    eligible = []
    for item in users:
        uid = item.get("user_id")
        if not uid:
            continue
        preferences = request("GET", "alert_preferences",
            "select=countries,genres&user_id=eq." + urllib.parse.quote(uid, safe=""))
        if preferences and matches(change.get("payload", {}), preferences[0]):
            eligible.append(uid)
    deliveries = [{"event_key": key, "user_id": uid} for uid in set(eligible)]
    if deliveries:
        request("POST", "alert_deliveries", "on_conflict=event_key,user_id",
                deliveries, "resolution=ignore-duplicates,return=minimal")
        count += len(deliveries)
print(f"Processed {processed} changes, staged up to {count} inbox records. No emails sent.")
