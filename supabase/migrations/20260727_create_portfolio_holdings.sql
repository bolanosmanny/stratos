create table public.portfolio_holdings (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  ticker text not null check (ticker = upper(ticker)),
  shares numeric(18, 6) not null check (shares > 0),
  purchase_price numeric(14, 4) not null check (purchase_price >= 0),
  purchase_date date not null,
  created_at timestamptz not null default now()
);

create index portfolio_holdings_user_id_idx
on public.portfolio_holdings (user_id);

alter table public.portfolio_holdings enable row level security;

create policy "Users can view their own portfolio holdings"
on public.portfolio_holdings
for select
to authenticated
using (auth.uid() = user_id);

create policy "Users can add their own portfolio holdings"
on public.portfolio_holdings
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "Users can update their own portfolio holdings"
on public.portfolio_holdings
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can delete their own portfolio holdings"
on public.portfolio_holdings
for delete
to authenticated
using (auth.uid() = user_id);

grant usage on schema public to authenticated;

grant select, insert, update, delete
on table public.portfolio_holdings
to authenticated;

grant usage, select
on sequence public.portfolio_holdings_id_seq
to authenticated;
