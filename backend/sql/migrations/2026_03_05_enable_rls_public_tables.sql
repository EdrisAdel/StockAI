alter table public.fundamentals_daily enable row level security;
alter table public.prices_daily enable row level security;
alter table public.indicators_daily enable row level security;
alter table public.run_log enable row level security;

drop policy if exists "public_read_fundamentals_daily" on public.fundamentals_daily;
create policy "public_read_fundamentals_daily"
  on public.fundamentals_daily
  for select
  to anon, authenticated
  using (true);

drop policy if exists "public_read_prices_daily" on public.prices_daily;
create policy "public_read_prices_daily"
  on public.prices_daily
  for select
  to anon, authenticated
  using (true);

drop policy if exists "public_read_indicators_daily" on public.indicators_daily;
create policy "public_read_indicators_daily"
  on public.indicators_daily
  for select
  to anon, authenticated
  using (true);

drop policy if exists "service_role_all_fundamentals_daily" on public.fundamentals_daily;
create policy "service_role_all_fundamentals_daily"
  on public.fundamentals_daily
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists "service_role_all_prices_daily" on public.prices_daily;
create policy "service_role_all_prices_daily"
  on public.prices_daily
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists "service_role_all_indicators_daily" on public.indicators_daily;
create policy "service_role_all_indicators_daily"
  on public.indicators_daily
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists "service_role_all_run_log" on public.run_log;
create policy "service_role_all_run_log"
  on public.run_log
  for all
  to service_role
  using (true)
  with check (true);