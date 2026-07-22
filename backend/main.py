from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os 
import requests
from dotenv import load_dotenv

from datetime import date, timedelta
from fastapi import HTTPException, Query

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"]
)

FMP_API_KEY = os.getenv("FMP_API_KEY")

@app.get("/")
def read_root():
    return {"message": "App is running"}

@app.get("/stock/{ticker}")
def get_stock(ticker: str):
    url = f"https://financialmodelingprep.com/stable/quote?symbol={ticker}&apikey={FMP_API_KEY}"
    response = requests.get(url)

    print(f"Status code: {response.status_code}")
    print(f"Raw response: {response.text[:500]}")

    try:
        data = response.json()
    except ValueError:
        return {"Error": "Data provider returned an invalid response."}

    return data

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
        response.raise_for_status()
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
        response.raise_for_status()
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

        quote_response.raise_for_status()
        income_response.raise_for_status()

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
    