-- Festival Radar V3: execute once in Supabase SQL Editor.
create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now()
);
create table if not exists public.favorites (
  user_id uuid not null references auth.users(id) on delete cascade,
  festival_id text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, festival_id)
);
create table if not exists public.alert_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  countries text[] not null default '{}',
  genres text[] not null default '{}',
  email_enabled boolean not null default false,
  updated_at timestamptz not null default now()
);
alter table public.profiles enable row level security;
alter table public.favorites enable row level security;
alter table public.alert_preferences enable row level security;
create policy "profiles_select_own" on public.profiles for select to authenticated using ((select auth.uid()) = user_id);
create policy "profiles_insert_own" on public.profiles for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "profiles_update_own" on public.profiles for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "favorites_select_own" on public.favorites for select to authenticated using ((select auth.uid()) = user_id);
create policy "favorites_insert_own" on public.favorites for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "favorites_delete_own" on public.favorites for delete to authenticated using ((select auth.uid()) = user_id);
create policy "preferences_select_own" on public.alert_preferences for select to authenticated using ((select auth.uid()) = user_id);
create policy "preferences_insert_own" on public.alert_preferences for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "preferences_update_own" on public.alert_preferences for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
