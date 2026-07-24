alter table public.document_chunks
add column if not exists section text not null default 'Risk Factors';

update public.document_chunks
set
    filing_type = '10-K',
    section = 'Risk Factors'
where filing_type = '10-K · Item 1A Risk Factors';

alter table public.document_chunks
drop constraint if exists document_chunks_accession_number_chunk_index_key;

alter table public.document_chunks
drop constraint if exists document_chunks_accession_section_chunk_unique;

alter table public.document_chunks
add constraint document_chunks_accession_section_chunk_unique
unique (accession_number, section, chunk_index);

drop function if exists public.match_document_chunks(vector, text, integer);

create function public.match_document_chunks(
    query_embedding vector(384),
    filter_ticker text,
    match_count integer default 6
)

returns table ( 
    id bigint,
    content text,
    filing_type text,
    section text,
    filing_date date,
    source_url text,
    similarity float
)
language sql 
stable
as $$
  select
    id,
    content,
    filing_type,
    section,
    filing_date,
    source_url,
    1 - (embedding <=> query_embedding) as similarity
  from public.document_chunks
  where ticker = upper(filter_ticker)
  order by embedding <=> query_embedding
  limit match_count;
$$;

grant execute
on function public.match_document_chunks(vector, text, integer)
to server_role;