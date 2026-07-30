create table public.research_history ( 
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users(id) on delete cascade,
    ticker text not null check (ticker = upper(ticker)),
    question text not null,
    answer text not null,
    citations jsonb not null default '[]'::jsonb,,
    created_at timestampz not null default now()
);

create index research_history_user_created_at_idx
on public.research_history (user_id, created_at desc);

alter table public.research_history enable row level security;

grant select, insert, delete
on table public.research_history
to authenticated;

grant usage, select
on sequence public.research_history_id_seq
to authenticated;

create policy "Users can view their own research history"
on public.research_history
for select
to authenticated
using (auth.uid() = user_id);

create policy "Users can save their own research history"
on public.research_history
for insert
to authenticated
with check (auth.uid() = user_id);

create policy "Users can delete their own research history"
on public.research_history
for delete
to authenticated
using (auth.uid() = user_id);