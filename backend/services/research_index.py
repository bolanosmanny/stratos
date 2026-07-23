import requests
from fastapi import HTTPException
from supabase import Client

from .embeddings import create_embeddings
from .sec_filings import get_latest_10k_risk_chunks

def index_latest_10k_risk_factors(
        ticker: str,
        sec_headers: dict[str, str],
        supabase: Client,
) -> dict:
    try:
        company, filing, chunks = get_latest_10k_risk_chunks(
            ticker,
            sec_headers
        )

        embeddings = create_embeddings(chunks)

        rows = [
            {
                "ticker": company["ticker"],
                "company_name": company["name"],
                "filing_type": "10-K · Item 1A Risk Factors",
                "filing_date": filing["filing_date"],
                "accession_number": filing["accession_number"],
                "source_url": filing["source_url"],
                "chunk_index": index,
                "content": chunk,
                "embedding": embedding,
            }
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings))
        ]

        batch_size = 20

        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]

            (
                supabase.table("document_chunks")
                .upsert(
                    batch,
                    on_conflict="accession_number,chunk_index",
                )
                .execute()
            )

        return { 
            "ticker": company["ticker"],
            "company_name": company["name"],
            "filing_date": filing["filing_date"],
            "chunks_indexed": len(rows),
            "source_url": filing["source_url"],
        }

    except HTTPException:
        raise
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"SEC filing request failed: {error}",
        )
    