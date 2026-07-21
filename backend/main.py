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

