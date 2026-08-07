from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os 
from dotenv import load_dotenv
from supabase import Client, create_client
import time
import logging
from routers.health import create_health_router
from routers.stock_context import create_stock_context_router
from routers.research import create_research_router
from routers.market_data import create_market_data_router
from routers.company import create_company_router

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

app.include_router(
    create_company_router(FMP_API_KEY)
)

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
