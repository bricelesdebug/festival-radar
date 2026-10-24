-- Festival Radar V4: run once in Supabase SQL Editor.
-- Events and notification candidates are server-managed; no email delivery is enabled.
create table if not exists public.alert_events (
  event_key text primary key,
  festival_id text not null,
  event_type text not null check (event_type in ('new_event','sales_start_changed','event_date_changed')),
  payload jsonb not null,
  detected_at timestamptz not null default now()
);
create table if not exists public.alert_deliveries (
  id bigint generated always as identity primary key,
  event_key text not null references public.alert_events(event_key) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'pending' check (status in ('pending','sent','failed','cancelled')),
  created_at timestamptz not null default now(),
  sent_at timestamptz,
  unique (event_key,user_id)
);
alter table public.alert_events enable row level security;
alter table public.alert_deliveries enable row level security;
-- Users can view their own notification history only.
create policy "deliveries_select_own" on public.alert_deliveries
  for select to authenticated using ((select auth.uid()) = user_id);
-- No public INSERT/UPDATE/DELETE policies: a future authenticated server worker
-- will use a server-side service credential to create events and deliveries.
-- Email sending is intentionally NOT implemented in this migration.
