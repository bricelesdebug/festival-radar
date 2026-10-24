-- Festival Radar V5 — authenticated users can read public event details
-- while alert_deliveries remains restricted to its recipient via existing RLS.
-- Safe to run repeatedly.
alter table public.alert_events enable row level security;
drop policy if exists "alert_events_read_authenticated" on public.alert_events;
create policy "alert_events_read_authenticated" on public.alert_events
  for select to authenticated using (true);
-- No client-side write access is granted to alert_events or alert_deliveries.
