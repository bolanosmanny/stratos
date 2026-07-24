import requests
from fastapi import HTTPException
from supabase import Client

from .embeddings import create_embeddings
from .sec_filings import get_latest_10k_sections

def index_latest_10k_sections(
        ticker: str,
        sec_headers: dict[str, str],
        supabase: Client,
) -> dict:
    try:
        company, filing, sections = get_latest_10k_sections(
            ticker,
            sec_headers
        )

        rows = []
        section_counts = []

        for section_data in sections:
            section = section_data["section"]
            chunks = section_data["chunks"]
            embeddings = create_embeddings(chunks)

            section_counts.append(
                {
                    "section": section,
                    "chunks_indexed": len(chunks),
                }
            )

            rows.extend(
                {
                    "ticker": company["ticker"],
                    "company_name": company["name"],
                    "filing_type": "10-K",
                    "section": section,
                    "filing_date": filing["filing_date"],
                    "accession_number": filing["accession_number"],
                    "source_url": filing["source_url"],
                    "chunk_index": index,
                    "content": chunk,
                    "embedding": embedding,
                }
                for index, (chunk, embedding) in enumerate(
                    zip(chunks, embeddings)
                )
            )

        batch_size = 20

        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]

            (
                supabase.table("document_chunks")
                .upsert(
                    batch,
                    on_conflict= "accession_number,section,chunk_index",
                )
                .execute()
            )

        return { 
            "ticker": company["ticker"],
            "company_name": company["name"],
            "filing_date": filing["filing_date"],
            "chunks_indexed": len(rows),
            "sections": section_counts,
            "source_url": filing["source_url"],
        }

    except HTTPException:
        raise
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail=f"SEC filing request failed: {error}",
        )