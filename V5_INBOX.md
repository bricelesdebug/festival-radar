# Festival Radar V5: internal notifications

The site already displays each authenticated user's own `alert_deliveries` through RLS.
The new `scripts/stage_inbox.py` prepares server-side inbox entries for users
who **favorited** a Ticketmaster event. No emails are sent.

**Not active yet.** The manual workflow only processes
`data/alert-candidates.json` when that file has been intentionally reviewed and
committed. The collector currently uploads candidates as a GitHub Actions artifact
and does not commit them, so running this workflow without an approved file does
nothing. This avoids mass false-positive notifications.

When ready:
- Set GitHub Actions variable `SUPABASE_URL` to the project URL.
- Set GitHub Actions **secret** `SUPABASE_SERVICE_ROLE_KEY` to the server-only
  service_role key from Supabase. NEVER paste it into chat or public source.
- Review candidate events carefully, especially heuristically identified festivals.
- Only after review, place approved candidates in `data/alert-candidates.json`.
- Manually run `Stage inbox notifications (manual only)` in GitHub Actions.
- Inspect a test account's private inbox. Delivery records are idempotent.

Before scheduling automatic distribution, implement a reliable review/validation
policy and safeguards against reused historical snapshots and false sale alerts.
