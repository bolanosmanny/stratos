import time

from fastapi import APIRouter, HTTPException, Query

from services.filing_timeline import get_company_filing_events
from services.news import get_company_news


def create_stock_context_router(
    alpha_vantage_api_key: str | None,
    sec_headers: dict[str, str],
) -> APIRouter:
    router = APIRouter()
    news_cache: dict[str, tuple[float, list[dict]]] = {}
    news_cache_ttl_seconds = 900

    @router.get("/stock/{ticker}/news")
    def get_stock_news(
        ticker: str,
        company_name: str = Query(default=""),
    ):
        if not alpha_vantage_api_key:
            raise HTTPException(
                status_code=500,
                detail="ALPHA_VANTAGE_API_KEY is not configured.",
            )

        symbol = ticker.strip().upper()
        cached_news = news_cache.get(symbol)
        now = time.time()

        if (
            cached_news
            and now - cached_news[0] < news_cache_ttl_seconds
        ):
            return {
                "symbol": symbol,
                "articles": cached_news[1],
            }

        articles = get_company_news(
            symbol,
            alpha_vantage_api_key,
            company_name,
        )

        news_cache[symbol] = (now, articles)

        return {
            "symbol": symbol,
            "articles": articles,
        }

    @router.get("/stock/{ticker}/events")
    def get_stock_events(ticker: str):
        symbol = ticker.strip().upper()

        return {
            "symbol": symbol,
            "events": get_company_filing_events(
                symbol,
                sec_headers,
            ),
        }

    return router