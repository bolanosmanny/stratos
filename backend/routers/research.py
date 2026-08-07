import logging
import time
from collections import defaultdict, deque
from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from supabase import Client

from services.research_answer import answer_research_question
from services.research_index import (
    index_latest_10k_sections,
    index_latest_10q_sections,
    index_latest_earnings_release_sections,
)
from services.retrieval import retrieve_relevant_chunks


logger = logging.getLogger("stratos.api.research")


class ResearchRequest(BaseModel):
    ticker: str
    question: str


def create_research_router(
    supabase: Client,
    sec_headers: dict[str, str],
    ollama_base_url: str,
    ollama_model: str,
    app_env: str,
    ingest_admin_token: str,
    research_rate_limit: int,
    research_rate_window_seconds: int,
) -> APIRouter:
    router = APIRouter()
    research_requests: dict[str, deque[float]] = defaultdict(deque)

    def get_client_key(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"

    def enforce_research_rate_limit(request: Request) -> None:
        client_key = get_client_key(request)
        now = time.monotonic()
        timestamps = research_requests[client_key]

        while (
            timestamps
            and now - timestamps[0] > research_rate_window_seconds
        ):
            timestamps.popleft()

        if len(timestamps) >= research_rate_limit:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Research request rate limit exceeded. "
                    "Please try again later."
                ),
            )

        timestamps.append(now)

    def require_ingest_admin_token(
        x_ingest_token: str | None = Header(default=None),
    ) -> None:
        if app_env != "production":
            return

        if (
            not ingest_admin_token
            or not x_ingest_token
            or not compare_digest(
                x_ingest_token,
                ingest_admin_token,
            )
        ):
            raise HTTPException(
                status_code=403,
                detail="Ingestion is disabled for public requests",
            )

    @router.post("/research")
    def research_company(
        request: ResearchRequest,
        http_request: Request,
    ):
        enforce_research_rate_limit(http_request)

        ticker = request.ticker.strip().upper()
        question = request.question.strip()

        if not ticker:
            raise HTTPException(
                status_code=400,
                detail="A ticker symbol is required",
            )

        if not question:
            raise HTTPException(
                status_code=400,
                detail="A research question is required",
            )

        result = answer_research_question(
            ticker,
            question,
            supabase,
            ollama_base_url,
            ollama_model,
        )

        return {
            "ticker": ticker,
            "question": question,
            "answer": result["answer"],
            "citations": result["citations"],
        }

    @router.get("/research/status")
    def research_status():
        try:
            response = (
                supabase.table("document_chunks")
                .select("id", count="exact")
                .limit(1)
                .execute()
            )

            return {
                "status": "connected",
                "indexed_chunks": response.count or 0,
            }
        except Exception:
            logger.exception("research_status_failed dependency=supabase")

            raise HTTPException(
                status_code=503,
                detail="Supabase dependency is unavailable.",
            )

    @router.post("/research/ingest/{ticker}")
    def ingest_latest_10k(
        ticker: str,
        _: None = Depends(require_ingest_admin_token),
    ):
        return index_latest_10k_sections(
            ticker,
            sec_headers,
            supabase,
        )

    @router.post("/research/ingest-quarterly/{ticker}")
    def ingest_latest_10q(
        ticker: str,
        _: None = Depends(require_ingest_admin_token),
    ):
        return index_latest_10q_sections(
            ticker,
            sec_headers,
            supabase,
        )

    @router.post("/research/ingest-earnings/{ticker}")
    def ingest_latest_earnings_release(
        ticker: str,
        _: None = Depends(require_ingest_admin_token),
    ):
        return index_latest_earnings_release_sections(
            ticker,
            sec_headers,
            supabase,
        )

    @router.post("/research/retrieve")
    def retrieve_research_chunks(request: ResearchRequest):
        ticker = request.ticker.strip().upper()
        question = request.question.strip()

        if not ticker or not question:
            raise HTTPException(
                status_code=400,
                detail="A ticker and research question are required",
            )

        matches = retrieve_relevant_chunks(
            ticker,
            question,
            supabase,
        )

        return {
            "ticker": ticker,
            "question": question,
            "matches": [
                {
                    "filing_type": match["filing_type"],
                    "filing_date": match["filing_date"],
                    "source_url": match["source_url"],
                    "similarity": round(match["similarity"], 3),
                    "excerpt": match["content"][:450] + "...",
                }
                for match in matches
            ],
        }

    return router
