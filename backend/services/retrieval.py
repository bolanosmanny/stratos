from supabase import Client

from .embeddings import create_embeddings

def retrieve_relevant_chunks(
        ticker: str,
        question: str,
        supabase: Client,
        match_count: int = 5,
) -> list[dict]:
    query_embedding = create_embeddings([question])[0]

    response = (
        supabase.rpc(
            "match_document_chunks",
            {
                "query_embedding": query_embedding,
                "filter_ticker": ticker.strip().upper(),
                "match_count": match_count,
            },
        )
        .execute()
    )

    return response.data or []

