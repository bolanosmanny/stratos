from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
import os 
import requests
from dotenv import load_dotenv
from datetime import date, timedelta
from collections import defaultdict, deque
from secrets import compare_digest
from pydantic import BaseModel
from supabase import Client, create_client
from services.research_index import (
    index_latest_10k_sections,
    index_latest_10q_sections,
    index_latest_earnings_release_sections,
)
from services.retrieval import retrieve_relevant_chunks
from services.research_answer import answer_research_question
import time
import logging
from routers.health import create_health_router
from routers.stock_context import create_stock_context_router

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger("stratos.api")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE__SECRET_KEY in backend/.env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")

if not SEC_USER_AGENT:
    raise RuntimeError("Missing SEC_USER_AGENT in backend/.env file")

SEC_HEADERS = {
    "User-Agent": SEC_USER_AGENT,
    "Accept-Encoding": "gzip, deflate",
}

OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:7b",
)

FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app = FastAPI()

@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed method=%s path=%s",
            request.method,
            request.url.path,
        )
        raise

    duration_ms = (time.perf_counter() - started_at) * 1000

    logger.info(
        "request_completed method=%s path=%s status=%s duration_ms=%.1f",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"]
)

FMP_API_KEY = os.getenv("FMP_API_KEY")

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
NEWS_CACHE: dict[str, tuple[float, list[dict]]] = {}
NEWS_CACHE_TTL_SECONDS = 900 # 15 minutes

QUOTE_CACHE: dict[str, tuple[float, dict]] = {}
QUOTE_CACHE_TTL_SECONDS = 60

APP_ENV = os.getenv("APP_ENV", "development").lower()
INGEST_ADMIN_TOKEN = os.getenv("INGEST_ADMIN_TOKEN", "")

RESEARCH_RATE_LIMIT = int(os.getenv("RESEARCH_RATE_LIMIT", "6"))
RESEARCH_RATE_WINDOW_SECONDS = int(
    os.getenv("RESEARCH_RATE_WINDOW_SECONDS", "600")
)
RESEARCH_REQUESTS: dict[str, deque[float]] = defaultdict(deque)

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
    timestamps = RESEARCH_REQUESTS[client_key]

    while ( 
        timestamps
        and now - timestamps[0] > RESEARCH_RATE_WINDOW_SECONDS
    ):
        timestamps.popleft()

    if len(timestamps) >= RESEARCH_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Research request rate limit exceeded. Please try again later.",
        )

    timestamps.append(now)

def require_ingest_admin_token(
        x_ingest_token: str | None = Header(default=None),     
) -> None:
    if APP_ENV != "production":
        return

    if (
        not INGEST_ADMIN_TOKEN
        or not x_ingest_token
        or not compare_digest(x_ingest_token, INGEST_ADMIN_TOKEN)
    ):
        raise HTTPException(
            status_code=403,
            detail="Ingestion is disabled for public requests",
        )

def check_fmp_response(response: requests.Response) -> None:
    if response.status_code == 429:
        raise HTTPException(
            status_code=429,
            detail="Market-data API limit reached. Please try again later.",
        )

    response.raise_for_status()

@app.get("/")
def read_root():
    return {"message": "App is running"}

app.include_router(create_health_router(supabase))

app.include_router(
    create_stock_context_router(
        ALPHA_VANTAGE_API_KEY,
        SEC_HEADERS,
    )
)

@app.get("/stock/{ticker}")
def get_stock(ticker: str):
    if not FMP_API_KEY:
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
                "apikey": FMP_API_KEY,
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

@app.get("/stocks/quotes")
def get_stock_quotes(
    symbols: str = Query(min_length=1),
):
    if not FMP_API_KEY:
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
        cached_quote = QUOTE_CACHE.get(symbol)

        if cached_quote and now - cached_quote[0] < QUOTE_CACHE_TTL_SECONDS:
            quotes.append(cached_quote[1])
            continue

        try: 
            response = requests.get(
                "https://financialmodelingprep.com/stable/quote",
                params={
                    "symbol": symbol,
                    "apikey": FMP_API_KEY,
                },
                timeout=15,
            )

            check_fmp_response(response)
            quote_data = response.json()

            if isinstance(quote_data, list) and quote_data:
                quote = quote_data[0]
                QUOTE_CACHE[symbol] = (now, quote)
                quotes.append(quote)

        except HTTPException:
            raise
        except (requests.RequestException, ValueError):
            raise HTTPException(
                status_code=502,
                detail="Unable to retrieve stock quote.",
            )

    return quotes

PERIOD_DAYS = {
    "1M": 30,
    "6M": 183,
    "1Y": 365,
    "5Y": 365 * 5,
}

@app.get("/stock/{ticker}/history")
def get_stock_history(
    ticker: str,
    period: str = Query(default="1Y", pattern="^(1M|6M|1Y|5Y)$"),
):
    if not FMP_API_KEY:
        raise HTTPException(status_code=500, detail="FMP_API_KEY is not configured.")
    
    symbol = ticker.strip().upper()
    start_date = date.today() - timedelta(days=PERIOD_DAYS[period])

    try:
        response = requests.get(
            "https://financialmodelingprep.com/stable/historical-price-eod/full",
            params={
                "symbol": symbol,
                "from": start_date.isoformat(),
                "to": date.today().isoformat(),
                "apikey": FMP_API_KEY,
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
    
    if not isinstance(data, list) or len(data) == 0:
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
        if all(key in item for key in ["date", "close", "high", "low", "volume"])
    ]

    return {
        "symbol": symbol,
        "period": period,
        "history": history,
    }

@app.get("/stock/{ticker}/profile")
def get_company_profile(ticker: str):
    if not FMP_API_KEY:
        raise HTTPException(status_code = 500, detail="FMP_API_KEY is not configured.")
    
    symbol = ticker.strip().upper()

    try:
        response = requests.get(
            "https://financialmodelingprep.com/stable/profile",
            params = {
                "symbol": symbol,
                "apikey": FMP_API_KEY,
            },
            timeout=15,
        )
        check_fmp_response(response)
        data = response.json()
    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Unable to retreive company profile data.",
        )

    if not isinstance(data, list) or len(data) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No company profile data found for {symbol}.",
        )
    
    profile = data[0]

    return { 
        "symbol": profile.get("symbol"),
        "companyName": profile.get("companyName"),
        "sector": profile.get("sector"),
        "industry": profile.get("industry"),
        "ceo": profile.get("ceo"),
        "website": profile.get("website"),
        "description": profile.get("description"),
        "country": profile.get("country"),
        "employees": profile.get("fullTimeEmployees"),
        "ipoDate": profile.get("ipoDate"),
        "image": profile.get("image"),
        "exchange": profile.get("exchange"),
    }

@app.get("/stock/{ticker}/fundamentals")
def get_company_fundamentals(ticker: str):
    if not FMP_API_KEY:
        raise HTTPException(status_code=500, detail="FMP_API_KEY is not configured.")
    
    symbol = ticker.strip().upper()

    try:
        quote_response = requests.get(
            "https://financialmodelingprep.com/stable/quote",
            params={"symbol": symbol, "apikey": FMP_API_KEY},
            timeout=15,  
        )
        income_response = requests.get(
            "https://financialmodelingprep.com/stable/income-statement",
            params={"symbol": symbol, "apikey": FMP_API_KEY},
            timeout=15,
        )

        check_fmp_response(quote_response)
        check_fmp_response(income_response)

        quote_data = quote_response.json()
        income_data = income_response.json()

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to retrieve fundamental data.",
        )
    
    if not isinstance(quote_data, list) or len(quote_data) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No fundamental data found for {symbol}.",
        )
    
    if not isinstance(income_data, list) or len(income_data) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No income statement data found for {symbol}.",
        )
    
    quote = quote_data[0]
    latest = income_data[0]
    previous = income_data[1] if len(income_data) > 1 else None

    revenue = latest.get("revenue")
    net_income = latest.get("netIncome")

    eps = latest.get("eps")
    pe_ratio = quote.get("pe")

    if pe_ratio is None and eps not in (None, 0):
        pe_ratio = quote.get("price") / eps

    revenue_growth = None
    if previous and previous.get("revenue") not in (None, 0):
        revenue_growth = (
            (revenue - previous.get("revenue")) / previous["revenue"]
        ) * 100

    net_margin = None
    if revenue not in (None, 0) and net_income is not None:
        net_margin = (net_income / revenue) * 100

    return { 
        "symbol": symbol,
        "fiscalDate": latest.get("date"),
        "peRatio": pe_ratio,
        "eps": eps,
        "dividendPerShare": quote.get("lastDiv"),
        "revenue": revenue,
        "revenueGrowth": revenue_growth,
        "netIncome": net_income,
        "netMargin": net_margin,
        "grossProfit": latest.get("grossProfit"),
        "operatingIncome": latest.get("operatingIncome"),
        "ebitda": latest.get("ebitda"),
    }

@app.get("/stock/{ticker}/financial-health")
def get_financial_health(ticker: str):
    if not FMP_API_KEY:
        raise HTTPException(status_code=500, detail="FMP_API_KEY is not configured.")
    
    symbol = ticker.strip().upper()

    try:
        balance_response = requests.get(
            "https://financialmodelingprep.com/stable/balance-sheet-statement",
            params={"symbol": symbol, "apikey": FMP_API_KEY},
            timeout=15,
        )

        cashflow_response = requests.get(
            "https://financialmodelingprep.com/stable/cash-flow-statement",
            params={"symbol": symbol, "apikey": FMP_API_KEY},
            timeout=15,
        )

        check_fmp_response(balance_response)
        check_fmp_response(cashflow_response)

        balance_data = balance_response.json()
        cashflow_data = cashflow_response.json()

    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve financial health data.",
        )
    
    if not isinstance(balance_data, list) or len(balance_data) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No balance sheet data found for {symbol}.",
        )
    
    if not isinstance(cashflow_data, list) or len(cashflow_data) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No cash flow data found for {symbol}.",
        )
    
    balance = balance_data[0]
    cashflow = cashflow_data[0]

    current_assets = balance.get("totalCurrentAssets")
    current_liabilities = balance.get("totalCurrentLiabilities")
    total_debt = balance.get("totalDebt")
    equity = balance.get("totalStockholdersEquity")
    operating_cash_flow = cashflow.get("operatingCashFlow")
    capital_expenditures = cashflow.get("capitalExpenditure")

    current_ratio = None
    if current_assets not in (None, 0) and current_liabilities not in (None, 0):
        current_ratio = current_assets / current_liabilities

    debt_to_equity = None
    if total_debt is not None and equity not in (None, 0):
        debt_to_equity = total_debt / equity

    free_cash_flow = cashflow.get("freeCashFlow")
    if(
        free_cash_flow is None
        and operating_cash_flow is not None
        and capital_expenditures is not None
    ):
        free_cash_flow = operating_cash_flow + capital_expenditures

    return {
        "symbol": symbol,
        "fiscalDate": balance.get("date"),
        "cashAndCashEquivalents": balance.get("cashAndCashEquivalents"),
        "totalDebt": total_debt,
        "totalAssets": balance.get("totalAssets"),
        "totalLiabilities": balance.get("totalLiabilities"),
        "shareholdersEquity": equity,
        "currentRatio": current_ratio,
        "debtToEquity": debt_to_equity,
        "operatingCashFlow": operating_cash_flow,
        "capitalExpenditures": capital_expenditures,
        "freeCashFlow": free_cash_flow,
    }

class ResearchRequest(BaseModel):
    ticker: str
    question: str

@app.post("/research")
def research_company(
    request: ResearchRequest,
    http_request: Request,
):
    enforce_research_rate_limit(http_request)

    ticker = request.ticker.strip().upper()
    question = request.question.strip()

    if not ticker:
        raise HTTPException(
            status_code = 400,
            detail = "A ticker symbol is required",
        )

    if not question:
        raise HTTPException(
            status_code = 400,
            detail = "A research question is required",
        )

    result = answer_research_question(
        ticker,
        question,
        supabase,
        OLLAMA_BASE_URL,
        OLLAMA_MODEL,
    )

    return { 
        "ticker": ticker,
        "question": question,
        "answer": result["answer"],
        "citations": result["citations"],
    }

@app.get("/research/status")
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
    except Exception as error:
        raise HTTPException(
            status_code = 503,
            detail = f"Supabase connection failed: {error}",
        )

@app.post("/research/ingest/{ticker}")
def ingest_latest_10k(
    ticker: str,
    _: None = Depends(require_ingest_admin_token),
):
    
    return index_latest_10k_sections(
        ticker,
        SEC_HEADERS,
        supabase,
)

@app.post("/research/ingest-quarterly/{ticker}")
def ingest_latest_10q(
    ticker: str,
    _: None = Depends(require_ingest_admin_token)
):
    
    return index_latest_10q_sections(
        ticker,
        SEC_HEADERS,
        supabase,
    )

@app.post("/research/ingest-earnings/{ticker}")
def ingest_latest_earnings_release(
    ticker: str,
    _: None = Depends(require_ingest_admin_token)
):
    
    return index_latest_earnings_release_sections(
        ticker,
        SEC_HEADERS,
        supabase,
    )

@app.post("/research/retrieve")
def retrieve_research_chunks(request: ResearchRequest):
    ticker = request.ticker.strip().upper()
    question = request.question.strip()

    if not ticker or not question:
        raise HTTPException(
            status_code = 400,
            detail = "A ticker and research question are required",
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