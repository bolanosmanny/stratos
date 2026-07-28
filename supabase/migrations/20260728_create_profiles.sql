begin;

create table public.profiles ( 
    id uuid primary key references auth.users (id) on delete cascade,
    display_name text check (char_length(display_name)) between 1 and 50),
    created_at timestampz not null default now(),
    updated_at timestampz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users can view their own profile"
on public.profiles
for select
to authenticated
using (auth.uid() = id);

create policy "Users can create their own profile"
on public.profiles
for insert
to authenticated
with check (auth.uid() = id);

create policy "Users can update their own profile"
on public.profiles
for update
to authenticated
using (auth.uid() = id)
with check (auth.uid() = id);

grant usage on schema public to authenticated;

grant select, insert, update
on public.profiles 
to authenticated;

insert into public.profiles (id, display_name)
select
    id,
    split_part(email, '@', 1)
from auth.users
on conflict (id) do nothing;

commit;