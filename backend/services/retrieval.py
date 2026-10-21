import math
import re
from collections import Counter

from supabase import Client

from .embeddings import create_embeddings


_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "from", "how", "in",
    "is", "of", "on", "or", "the", "to", "was", "were", "what", "which", "with",
}


def _tokens(text: str) -> list[str]:
    return [
        word for word in re.findall(r"[a-z0-9]+", text.casefold())
        if word not in _STOP_WORDS
    ]


def _keyword_top_chunks(question: str, rows: list[dict], count: int) -> list[dict]:
    """BM25-rank a single ticker's indexed chunks; no new database schema needed."""
    if not rows:
        return []
    terms = _tokens(question)
    docs = [Counter(_tokens(row["content"])) for row in rows]
    document_frequency = Counter(term for doc in docs for term in doc)
    average_length = sum(sum(doc.values()) for doc in docs) / len(docs)
    scored = []
    for row, doc in zip(rows, docs):
        length = sum(doc.values())
        score = 0.0
        for term in terms:
            frequency = doc[term]
            if frequency == 0:
                continue
            inverse_frequency = math.log(
                1 + (len(rows) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            score += inverse_frequency * frequency * 2.2 / (
                frequency + 1.2 * (0.25 + 0.75 * length / max(average_length, 1))
            )
        scored.append((score, row["id"], row))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [row for score, _, row in scored[:count] if score > 0]


def _ticker_chunks(ticker: str, supabase: Client) -> list[dict]:
    rows = []
    for start in range(0, 10000, 1000):
        page = (
            supabase.table("document_chunks")
            .select("id,content,filing_type,section,filing_date,source_url")
            .eq("ticker", ticker.strip().upper())
            .order("id")
            .range(start, start + 999)
            .execute()
            .data
        )
        rows.extend(page)
        if len(page) < 1000:
            return rows
    raise ValueError("Too many indexed chunks for one ticker; add pagination")

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


def retrieve_relevant_chunks_hybrid(
        ticker: str,
        question: str,
        supabase: Client,
        match_count: int = 5,
) -> list[dict]:
    """Fuse semantic and keyword top-k with reciprocal rank fusion."""
    vector = retrieve_relevant_chunks(ticker, question, supabase, match_count)
    keyword = _keyword_top_chunks(
        question, _ticker_chunks(ticker, supabase), match_count
    )
    candidates = {row["id"]: row for row in keyword}
    candidates.update({row["id"]: row for row in vector})
    scores = Counter()
    for ranking in (vector, keyword):
        for rank, row in enumerate(ranking, 1):
            scores[row["id"]] += 1 / (60 + rank)
    return [
        candidates[chunk_id]
        for chunk_id in sorted(candidates, key=lambda item: (-scores[item], item))[:match_count]
    ]
