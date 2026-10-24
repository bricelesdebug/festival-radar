#!/usr/bin/env python3
"""Read-only connectivity check for Festival Radar Supabase server credentials.
Does not return user data or print credentials.
"""
import os
import urllib.request
import urllib.error

base=os.environ.get("SUPABASE_URL","").strip().rstrip("/")
key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY","").strip()
if not base.startswith("https://") or not key:
    raise SystemExit("Missing SUPABASE_URL variable or SUPABASE_SERVICE_ROLE_KEY secret.")
for table in ("alert_events","alert_deliveries","favorites"):
    req=urllib.request.Request(
        base+"/rest/v1/"+table+"?select=*&limit=0",
        headers={"apikey":key,"Authorization":"Bearer "+key,
                 "Accept":"application/json"},
        method="GET")
    try:
        with urllib.request.urlopen(req,timeout=15) as response:
            if response.status != 200:
                raise SystemExit("Unexpected response for "+table)
        print(table+": accessible (no rows retrieved)")
    except urllib.error.HTTPError as e:
        raise SystemExit(table+": HTTP "+str(e.code)+"; check table and credentials") from None
    except urllib.error.URLError:
        raise SystemExit(table+": connection error; check project URL") from None
print("Supabase read-only connectivity check passed. No notifications sent.")
