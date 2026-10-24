# Festival Radar V4 — alert detection (preparation)

The V4 code does **not** send emails or connect to Resend. It prepares a secure
schema and an offline comparison script.

1. In Supabase SQL Editor, execute `supabase/alerts_v4.sql` once.
2. Save a known baseline Ticketmaster snapshot as `previous.json`.
3. After a later collection, run:
   `python scripts/detect_alerts.py previous.json data/festivals.json -o data/alert-candidates.json`
4. Review the output. New events, changed sale-start timestamps and changed event
   dates are **candidates**, not verified ticket-release announcements.
5. Do not use an empty snapshot as a baseline; it would classify every existing
   event as new. No notifications are sent.

**Before activating email:** implement a server-only worker with secure credentials,
consent verification, preference matching, deduplication via `alert_deliveries`,
rate limiting, unsubscribe handling and monitoring. The browser must never receive
the Resend API key or Supabase service-role/secret key.

The existing `alert_preferences` table defaults `email_enabled` to false.
Existing users must explicitly opt in. The current website does not yet offer
that opt-in interface.
