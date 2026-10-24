#!/usr/bin/env python3
"""Compare two Ticketmaster snapshots and produce *review-only* alert candidates.

Usage: python scripts/detect_alerts.py old.json new.json -o candidates.json
No network calls, credentials, database writes or email sends.
The first snapshot should be a known baseline; never alert on all existing
events merely because the old snapshot is empty.
"""
import argparse
import json
from pathlib import Path

def read_events(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        raise ValueError(f"Invalid snapshot: {path}")
    result = {}
    for event in data["events"]:
        if isinstance(event, dict) and event.get("id"):
            result[str(event["id"])] = event
    return result

def detect(previous, current):
    changes = []
    for event_id, event in sorted(current.items()):
        old = previous.get(event_id)
        if old is None:
            changes.append({"event_key": f"{event_id}:new_event", "festival_id": event_id,
                            "event_type": "new_event", "payload": event})
            continue
        for field, event_type in (("salesStart", "sales_start_changed"),
                                  ("date", "event_date_changed")):
            before, after = old.get(field), event.get(field)
            if before != after and after:
                # Key includes new value: a later legitimate change gets a distinct event.
                changes.append({"event_key": f"{event_id}:{event_type}:{after}",
                                "festival_id": event_id, "event_type": event_type,
                                "payload": {"name": event.get("name"), "before": before,
                                            "after": after, "url": event.get("url")}})
    return changes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("previous")
    parser.add_argument("current")
    parser.add_argument("-o", "--output", default="data/alert-candidates.json")
    args = parser.parse_args()
    previous, current = read_events(args.previous), read_events(args.current)
    changes = detect(previous, current)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"delivery_enabled": False,
                                  "note": "Candidates only. Review before notification.",
                                  "changes": changes}, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(f"Detected {len(changes)} candidate changes; no emails sent.")

if __name__ == "__main__":
    main()
