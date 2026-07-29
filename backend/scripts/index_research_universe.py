import os
import sys
import time

from dotenv import load_dotenv
from supabase import Client, create_client

from services.research_index import (
    index_latest_10k_sections,
    index_latest_10q_sections,
    index_latest_earnings_release_sections,
)


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

FILING_INDEXERS = [
    ("10-K", index_latest_10k_sections),
    ("10-Q", index_latest_10q_sections),
    ("8-K Earnings Release", index_latest_earnings_release_sections),
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

        for filing_type, indexer in FILING_INDEXERS:
            try:
                result = indexer(
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
                    f"✓ {filing_type}: "
                    f"{result['chunks_indexed']} chunks indexed "
                    f"({section_summary})"
                )
                successful.append(f"{ticker}{filing_type}")

            except Exception as error:
                print(f"✗ {filing_type}: {error}")
                failed.append(f"{ticker}{filing_type}")

            time.sleep(0.3)

    print("\n--- Indexing summary ---")
    print(f"Successful filing jobs: {len(successful)}")
    print(f"Failed filing jobs: {len(failed)}")

    if failed:
        print(f"Failed tickers: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()