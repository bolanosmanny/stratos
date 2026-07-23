from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os 
import requests
from dotenv import load_dotenv

from datetime import date, timedelta
from fastapi import HTTPException, Query

from pydantic import BaseModel

from supabase import Client, create_client
from services.research_index import index_latest_10k_risk_factors
from services.retrieval import retrieve_relevant_chunks

load_dotenv()

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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

FMP_API_KEY = os.getenv("FMP_API_KEY")

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
def research_company(request: ResearchRequest):
    symbol = request.ticker.strip().upper()
    question = request.question.strip()

    if not symbol:
        raise HTTPException(
            status_code = 400,
            detail = "A ticker symbol is required",
        )

    if not question:
        raise HTTPException(
            status_code = 400,
            detail = "A research question is required",
        )

    return { 
        "ticker": symbol,
        "question": question,
        "answer": (
            f"Sparky received your question about {symbol}."
            " SEC filing retrieval and source-cited analysis will be connected next."
        ),
        "citations":[],
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
def ingest_latest_10k(ticker: str):
    return index_latest_10k_risk_factors(
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