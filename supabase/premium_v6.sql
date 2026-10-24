-- Preparation only. Apply after schema.sql. No payment provider or checkout.
begin;
create table if not exists public.subscriptions (
  user_id uuid primary key references auth.users(id) on delete cascade,
  plan text not null default 'free' check (plan in ('free', 'premium')),
  status text not null default 'inactive' check (status in ('inactive','trialing','active','past_due','cancelled')),
  current_period_end timestamptz,
  provider_customer_id text unique,
  provider_subscription_id text unique,
  updated_at timestamptz not null default now(),
  check (plan <> 'premium' or status not in ('active','trialing') or current_period_end is not null)
);
alter table public.subscriptions enable row level security;
-- Clients may only read safe entitlement fields. They cannot grant Premium.
revoke all on public.subscriptions from anon, authenticated;
grant select (user_id, plan, status, current_period_end) on public.subscriptions to authenticated;
drop policy if exists subscriptions_select_own on public.subscriptions;
create policy subscriptions_select_own on public.subscriptions
  for select to authenticated using ((select auth.uid()) = user_id);
-- A future server-only, signature-verified webhook will manage this table.
-- Its provider event ledger makes retried webhooks idempotent; inaccessible to clients.
create table if not exists public.billing_events (
  provider_event_id text primary key,
  processed_at timestamptz not null default now()
);
alter table public.billing_events enable row level security;
revoke all on public.billing_events from anon, authenticated;
commit;
