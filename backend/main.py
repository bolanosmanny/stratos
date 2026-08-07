from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os 
import requests
from dotenv import load_dotenv
from supabase import Client, create_client
import time
import logging
from routers.health import create_health_router
from routers.stock_context import create_stock_context_router
from routers.research import create_research_router
from routers.market_data import create_market_data_router

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

APP_ENV = os.getenv("APP_ENV", "development").lower()
INGEST_ADMIN_TOKEN = os.getenv("INGEST_ADMIN_TOKEN", "")

RESEARCH_RATE_LIMIT = int(os.getenv("RESEARCH_RATE_LIMIT", "6"))
RESEARCH_RATE_WINDOW_SECONDS = int(
    os.getenv("RESEARCH_RATE_WINDOW_SECONDS", "600")
)

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

app.include_router(
    create_market_data_router(
        FMP_API_KEY)
)

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

app.include_router(
    create_research_router(
        supabase,
        SEC_HEADERS,
        OLLAMA_BASE_URL,
        OLLAMA_MODEL,
        APP_ENV,
        INGEST_ADMIN_TOKEN,
        RESEARCH_RATE_LIMIT,
        RESEARCH_RATE_WINDOW_SECONDS,
    )
)
