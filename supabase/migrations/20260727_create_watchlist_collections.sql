begin;

create table public.watchlist_collections (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null check (char_length(trim(name)) between 1 and 60),
  created_at timestamptz not null default now(),
  unique (user_id, name)
);

create table public.watchlist_items (
  id bigint generated always as identity primary key,
  watchlist_id bigint not null references public.watchlist_collections (id) on delete cascade,
  ticker text not null check (ticker = upper(ticker)),
  created_at timestamptz not null default now(),
  unique (watchlist_id, ticker)
);

create index watchlist_collections_user_id_idx
on public.watchlist_collections (user_id);

create index watchlist_items_watchlist_id_idx
on public.watchlist_items (watchlist_id);

alter table public.watchlist_collections enable row level security;
alter table public.watchlist_items enable row level security;

create policy "Users can view their own watchlist collections"
on public.watchlist_collections
for select
to authenticated
using (auth.uid() = user_id);

create policy "Users can create their own watchlist collections"
on public.watchlist_collections
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "Users can update their own watchlist collections"
on public.watchlist_collections
for update
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can delete their own watchlist collections"
on public.watchlist_collections
for delete
to authenticated
using (auth.uid() = user_id);

create policy "Users can view items in their own watchlists"
on public.watchlist_items
for select
to authenticated
using (
  exists (
    select 1
    from public.watchlist_collections
    where watchlist_collections.id = watchlist_items.watchlist_id
      and watchlist_collections.user_id = auth.uid()
  )
);

create policy "Users can add items to their own watchlists"
on public.watchlist_items
for insert
to authenticated
with check (
  exists (
    select 1
    from public.watchlist_collections
    where watchlist_collections.id = watchlist_items.watchlist_id
      and watchlist_collections.user_id = auth.uid()
  )
);

create policy "Users can update items in their own watchlists"
on public.watchlist_items
for update
to authenticated
using (
  exists (
    select 1
    from public.watchlist_collections
    where watchlist_collections.id = watchlist_items.watchlist_id
      and watchlist_collections.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.watchlist_collections
    where watchlist_collections.id = watchlist_items.watchlist_id
      and watchlist_collections.user_id = auth.uid()
  )
);

create policy "Users can delete items from their own watchlists"
on public.watchlist_items
for delete
to authenticated
using (
  exists (
    select 1
    from public.watchlist_collections
    where watchlist_collections.id = watchlist_items.watchlist_id
      and watchlist_collections.user_id = auth.uid()
  )
);

grant usage on schema public to authenticated;

grant select, insert, update, delete
on public.watchlist_collections
to authenticated;

grant select, insert, update, delete
on public.watchlist_items
to authenticated;

grant usage, select
on sequence public.watchlist_collections_id_seq
to authenticated;

grant usage, select
on sequence public.watchlist_items_id_seq
to authenticated;

insert into public.watchlist_collections (user_id, name)
select distinct user_id, 'My Watchlist'
from public.watchlists
on conflict (user_id, name) do nothing;

insert into public.watchlist_items (watchlist_id, ticker)
select collections.id, upper(watchlists.ticker)
from public.watchlists
join public.watchlist_collections as collections
  on collections.user_id = watchlists.user_id
  and collections.name = 'My Watchlist'
on conflict (watchlist_id, ticker) do nothing;

commit;