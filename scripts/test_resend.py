#!/usr/bin/env python3
"""Manually triggered Resend smoke test, never a bulk notification sender."""
import json
import os
import urllib.request
import urllib.error

key = os.environ.get("RESEND_API_KEY")
recipient = os.environ.get("RESEND_TEST_EMAIL")
if not key or not recipient:
    raise SystemExit("Configure RESEND_API_KEY and RESEND_TEST_EMAIL GitHub secrets.")
if any(x in recipient for x in (",", ";", "\n", "\r")) or "@" not in recipient:
    raise SystemExit("RESEND_TEST_EMAIL must contain exactly one email address.")
payload = {
    "from": "Festival Radar Test <onboarding@resend.dev>",
    "to": [recipient],
    "subject": "Festival Radar — test de notification",
    "text": "Bonjour ! Ceci est un email de test de Festival Radar. Aucune alerte automatique n'est activée."
}
request = urllib.request.Request(
    "https://api.resend.com/emails",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.load(response)
        if not result.get("id"):
            raise SystemExit("Resend did not return a message ID.")
        print("Resend accepted the test message. Check delivery in the Resend dashboard.")
except urllib.error.HTTPError as exc:
    # Only print allowlisted diagnostic fields; never print headers, addresses or keys.
    try:
        body = json.loads(exc.read().decode("utf-8", errors="replace"))
    except (ValueError, UnicodeError):
        body = {}
    code = body.get("name") or body.get("code") or "unknown"
    if not isinstance(code, str) or len(code) > 80:
        code = "unknown"
    print(f"Resend rejected request: HTTP {exc.code}; error type: {code}")
    if exc.code == 403:
        print("Check sender domain verification, sandbox recipient restrictions, and API key permissions.")
    raise SystemExit(1)
