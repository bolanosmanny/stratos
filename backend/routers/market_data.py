import time
from datetime import date, timedelta

import requests
from fastapi import APIRouter, HTTPException, Query

from services.fmp import check_fmp_response


PERIOD_DAYS = {
    "1M": 30,
    "6M": 183,
    "1Y": 365,
    "5Y": 365 * 5,
}


def create_market_data_router(
    fmp_api_key: str | None,
) -> APIRouter:
    router = APIRouter()
    quote_cache: dict[str, tuple[float, dict]] = {}
    quote_cache_ttl_seconds = 60

    @router.get("/stock/{ticker}")
    def get_stock(ticker: str):
        if not fmp_api_key:
            raise HTTPException(
                status_code=500,
                detail="FMP_API_KEY is not configured.",
            )

        symbol = ticker.strip().upper()

        try:
            response = requests.get(
                "https://financialmodelingprep.com/stable/quote",
                params={
                    "symbol": symbol,
                    "apikey": fmp_api_key,
                },
                timeout=15,
            )

            check_fmp_response(response)
            return response.json()

        except HTTPException:
            raise
        except (requests.RequestException, ValueError):
            raise HTTPException(
                status_code=502,
                detail="Unable to retrieve stock quote data.",
            )

    @router.get("/stocks/quotes")
    def get_stock_quotes(
        symbols: str = Query(min_length=1),
    ):
        if not fmp_api_key:
            raise HTTPException(
                status_code=500,
                detail="FMP_API_KEY is not configured.",
            )

        ticker_list = list(
            dict.fromkeys(
                symbol.strip().upper()
                for symbol in symbols.split(",")
                if symbol.strip()
            )
        )

        if not ticker_list:
            raise HTTPException(
                status_code=400,
                detail="Provide at least one ticker symbol.",
            )

        if len(ticker_list) > 50:
            raise HTTPException(
                status_code=400,
                detail="Maximum of 50 ticker symbols allowed.",
            )

        quotes = []
        now = time.time()

        for symbol in ticker_list:
            cached_quote = quote_cache.get(symbol)

            if (
                cached_quote
                and now - cached_quote[0] < quote_cache_ttl_seconds
            ):
                quotes.append(cached_quote[1])
                continue

            try:
                response = requests.get(
                    "https://financialmodelingprep.com/stable/quote",
                    params={
                        "symbol": symbol,
                        "apikey": fmp_api_key,
                    },
                    timeout=15,
                )

                check_fmp_response(response)
                quote_data = response.json()

                if isinstance(quote_data, list) and quote_data:
                    quote = quote_data[0]
                    quote_cache[symbol] = (now, quote)
                    quotes.append(quote)

            except HTTPException:
                raise
            except (requests.RequestException, ValueError):
                raise HTTPException(
                    status_code=502,
                    detail="Unable to retrieve stock quote.",
                )

        return quotes

    @router.get("/stock/{ticker}/history")
    def get_stock_history(
        ticker: str,
        period: str = Query(
            default="1Y",
            pattern="^(1M|6M|1Y|5Y)$",
        ),
    ):
        if not fmp_api_key:
            raise HTTPException(
                status_code=500,
                detail="FMP_API_KEY is not configured.",
            )

        symbol = ticker.strip().upper()
        start_date = date.today() - timedelta(
            days=PERIOD_DAYS[period]
        )

        try:
            response = requests.get(
                "https://financialmodelingprep.com/"
                "stable/historical-price-eod/full",
                params={
                    "symbol": symbol,
                    "from": start_date.isoformat(),
                    "to": date.today().isoformat(),
                    "apikey": fmp_api_key,
                },
                timeout=15,
            )
            check_fmp_response(response)
            data = response.json()
        except requests.RequestException:
            raise HTTPException(
                status_code=502,
                detail="Unable to retrieve historical market data.",
            )

        if not isinstance(data, list) or not data:
            raise HTTPException(
                status_code=404,
                detail=f"No historical data found for {symbol}.",
            )

        history = [
            {
                "date": item["date"],
                "close": item["close"],
                "high": item["high"],
                "low": item["low"],
                "volume": item["volume"],
            }
            for item in reversed(data)
            if all(
                key in item
                for key in [
                    "date",
                    "close",
                    "high",
                    "low",
                    "volume",
                ]
            )
        ]

        return {
            "symbol": symbol,
            "period": period,
            "history": history,
        }

    return router