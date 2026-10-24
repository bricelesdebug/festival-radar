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
    # Report only safe metadata. Strip any addresses/tokens from diagnostic text.
    import re
    raw = exc.read().decode("utf-8", errors="replace")
    try:
        body = json.loads(raw)
    except ValueError:
        body = {}
    print(f"Resend HTTP status: {exc.code}")
    if isinstance(body, dict):
        for field in ("name", "code", "statusCode", "message"):
            value = body.get(field)
            if not isinstance(value, (str, int)):
                continue
            value = str(value)
            value = re.sub(r"re_[A-Za-z0-9_\\-]+", "[REDACTED_KEY]", value)
            value = re.sub(r"[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", value)
            value = value.replace(key, "[REDACTED_KEY]").replace(recipient, "[REDACTED_EMAIL]")
            print(f"Resend {field}: {value[:300]}")
    else:
        print("Resend response is not a JSON object.")
    raise SystemExit(1)
