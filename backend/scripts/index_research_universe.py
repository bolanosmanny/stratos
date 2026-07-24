import os
import sys
import time

from dotenv import load_dotenv
from supabase import Client, create_client

from services.research_index import index_latest_10k_sections


TICKER_TAPE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "GOOGL",
    "AMZN",
    "META",
    "JPM",
    "V",
    "WMT",
    "UNH",
    "XOM",
    "DIS",
    "NFLX",
    "INTC",
    "AMD",
    "COST",
]


def create_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    secret_key = os.getenv("SUPABASE_SECRET_KEY")

    if not url or not secret_key:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_SECRET_KEY in backend/.env."
        )

    return create_client(url, secret_key)


def main() -> None:
    load_dotenv()

    sec_user_agent = os.getenv("SEC_USER_AGENT")

    if not sec_user_agent:
        raise RuntimeError("Missing SEC_USER_AGENT in backend/.env.")

    sec_headers = {
        "User-Agent": sec_user_agent,
        "Accept-Encoding": "gzip, deflate",
    }
    supabase = create_supabase_client()

    successful = []
    failed = []

    for position, ticker in enumerate(TICKER_TAPE, start=1):
        print(f"\n[{position}/{len(TICKER_TAPE)}] Indexing {ticker}...")

        try:
            result = index_latest_10k_sections(
                ticker,
                sec_headers,
                supabase,
            )

            section_summary = ", ".join(
                (
                    f"{section['section']}: "
                    f"{section['chunks_indexed']} chunks"
                )
                for section in result["sections"]
            )

            print(
                f"✓ {ticker}: {result['chunks_indexed']} chunks indexed "
                f"({section_summary})"
            )
            successful.append(ticker)

        except Exception as error:
            print(f"✗ {ticker}: {error}")
            failed.append(ticker)

        time.sleep(0.2)

    print("\n--- Indexing summary ---")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print(f"Failed tickers: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()