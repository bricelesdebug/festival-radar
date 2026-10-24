#!/usr/bin/env python3
"""Offline personalized candidate preview. Never connects to a delivery provider.

Input preferences: {"users": [{"user_id": "...", "favorites": ["..."],
"countries": ["FR"], "genres": ["Techno"], "email_enabled": false}]}.
Output contains private user IDs: never put it in the public data directory.
"""
import argparse
import json
from pathlib import Path


def matches(event, preference):
    """All populated filters apply; broad Electronic never implies Techno/House."""
    countries = preference.get('countries', [])
    genres = {str(g).casefold() for g in preference.get('genres', [])}
    actual = {str(g).casefold() for g in event.get('genres', [])}
    return ((not countries or event.get('countryCode') in countries)
            and (not genres or bool(genres & actual)))


def preview(changes, users):
    rows, seen = [], set()
    for user in users:
        for change in changes:
            uid, key, fid = user.get('user_id'), change.get('event_key'), change.get('festival_id')
            if not uid or not key or fid not in user.get('favorites', []):
                continue
            if not matches(change.get('payload', {}), user):
                continue
            if (uid, key) in seen:
                continue
            seen.add((uid, key))
            rows.append({'user_id':uid, 'event_key':key,
                         'review_required':True, 'delivery_enabled':False,
                         'email_consent':user.get('email_enabled') is True})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('candidates', type=Path)
    parser.add_argument('preferences', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    public = Path(__file__).resolve().parents[1]
    if args.output.resolve().is_relative_to(public):
        raise SystemExit('Private previews must be saved outside the published repository')
    changes = json.loads(args.candidates.read_text())['changes']
    users = json.loads(args.preferences.read_text())['users']
    rows = preview(changes, users)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'delivery_enabled':False, 'matches':rows}, indent=2)+'\n')
    print(f'{len(rows)} private matches need review; no emails or database writes.')


if __name__ == '__main__':
    main()
