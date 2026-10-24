#!/usr/bin/env python3
"""Stage internal inbox notifications for favorited Ticketmaster events.

Server-only. Reads a review-only candidate JSON file; no email delivery.
Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in server secrets.
Only users who explicitly follow the event get an inbox entry.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

BASE = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
if not BASE.startswith("https://") or not KEY:
    raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
if len(sys.argv) != 2:
    raise SystemExit("Usage: python scripts/stage_inbox.py <candidate-json>")

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
changes = data.get("changes", [])
if not isinstance(changes, list):
    raise SystemExit("Invalid candidate file")

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
for change in changes:
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
    deliveries = [{"event_key": key, "user_id": item["user_id"]}
                  for item in users if item.get("user_id")]
    if deliveries:
        request("POST", "alert_deliveries", "on_conflict=event_key,user_id",
                deliveries, "resolution=ignore-duplicates,return=minimal")
        count += len(deliveries)
print(f"Staged up to {count} inbox records for favorited events. No emails sent.")
