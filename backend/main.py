from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os 
import requests
from dotenv import load_dotenv

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

