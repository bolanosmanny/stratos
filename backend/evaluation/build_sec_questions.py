"""Build a source-anchored draft evaluation set from the indexed SEC corpus.

Generated questions are *draft labels*: inspect them before using the scores as
externally reported answer-quality metrics. The quote and answer are checked
against the actual indexed chunk, but that alone is not semantic review.
"""

import argparse
import json
import os
import random
import re
from pathlib import Path

import requests
from dotenv import load_dotenv
from supabase import create_client


TICKERS = [
    "AAPL", "AMD", "AMZN", "COST", "DIS", "GOOGL", "INTC", "JPM",
    "META", "MSFT", "NFLX", "NVDA", "TSLA", "UNH", "V", "WMT", "XOM",
]
FILING_TYPES = ["10-K", "10-Q", "8-K · Earnings Release"]
TARGET_SUPPORTED = 42


def generate_question(content: str, base_url: str, model: str) -> dict | None:
    prompt = (
        "Create ONE realistic financial-research question answerable from this "
        "SEC filing excerpt. Prefer a specific business or financial fact. "
        "Return JSON keys question, expected_answer, evidence_quote. "
        "The expected_answer must be a short exact substring of evidence_quote; "
        "evidence_quote must be one contiguous exact substring of the excerpt. "
        "The question must not reveal the answer or ask about the excerpt itself. "
        "Avoid share prices, predictions, and trivial filing metadata.\n\n"
        f"Excerpt:\n{content[:2100]}"
    )
    response = requests.post(
        f"{base_url.rstrip('/')}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "num_predict": 350},
        },
        timeout=180,
    )
    response.raise_for_status()
    try:
        result = json.loads(response.json()["message"]["content"])
    except (KeyError, ValueError, TypeError):
        return None
    if not isinstance(result, dict):
        return None
    question = str(result.get("question", "")).strip()
    answer = str(result.get("expected_answer", "")).strip()
    quote = str(result.get("evidence_quote", "")).strip()
    if not (question.endswith("?") and 3 <= len(answer) <= 100):
        return None
    if not (answer in quote and quote in content and 30 <= len(quote) <= 600):
        return None
    if answer.casefold() in question.casefold():
        return None
    return {"question": question, "expected_answer": answer, "evidence_quote": quote}


def unsupported_questions() -> list[dict]:
    # These ask for information outside the indexed SEC excerpts, not merely
    # facts that are difficult for a particular retriever to find.
    requests = [
        ("AAPL", "What will Apple's stock price close at on December 31, 2030?"),
        ("MSFT", "What is Microsoft's unpublished internal cloud budget for 2030?"),
        ("NVDA", "How many GPUs will NVIDIA sell in fiscal 2031?"),
        ("AMZN", "What will Amazon's next unannounced acquisition be?"),
        ("GOOGL", "What did Alphabet's board privately decide in its October 2030 meeting?"),
        ("META", "What is Meta's confidential 2030 product roadmap?"),
        ("TSLA", "What will Tesla's exact 2030 net income be?"),
        ("JPM", "What is JPMorgan's private customer account password policy for 2030?"),
    ]
    return [
        {
            "id": f"U{index:02d}",
            "ticker": ticker,
            "question": question,
            "answerable": False,
            "expected_answer": None,
            "gold_chunk_id": None,
            "source_url": None,
            "filing_type": None,
            "section": None,
            "filing_date": None,
            "evidence_quote": None,
            "label_status": "human_authored_out_of_corpus",
        }
        for index, (ticker, question) in enumerate(requests, 1)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen2.5:7b")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    rng = random.Random(20261021)
    labels = []
    pairs = [(ticker, filing_type) for ticker in TICKERS for filing_type in FILING_TYPES]
    rng.shuffle(pairs)

    for ticker, filing_type in pairs:
        if len(labels) >= TARGET_SUPPORTED:
            break
        rows = (
            supabase.table("document_chunks")
            .select("id,ticker,filing_type,section,filing_date,source_url,content")
            .eq("ticker", ticker)
            .eq("filing_type", filing_type)
            .limit(500)
            .execute()
            .data
        )
        candidates = [
            row for row in rows
            if 450 <= len(row["content"]) <= 2400
            and len(re.findall(r"\b\d[\d,.%$]*\b", row["content"])) >= 2
        ]
        rng.shuffle(candidates)
        for row in candidates[:8]:
            generated = generate_question(row["content"], args.ollama_url, args.model)
            if generated is None:
                continue
            labels.append({
                "id": f"S{len(labels) + 1:02d}",
                "ticker": ticker,
                "question": generated["question"],
                "answerable": True,
                "expected_answer": generated["expected_answer"],
                "gold_chunk_id": row["id"],
                "source_url": row["source_url"],
                "filing_type": row["filing_type"],
                "section": row["section"],
                "filing_date": row["filing_date"],
                "evidence_quote": generated["evidence_quote"],
                "label_status": "source_span_verified_pending_human_review",
            })
            print(f"{labels[-1]['id']} {ticker} {filing_type}: {generated['question']}", flush=True)
            break

    if len(labels) != TARGET_SUPPORTED:
        raise RuntimeError(f"Only generated {len(labels)}/{TARGET_SUPPORTED} supported labels")
    labels.extend(unsupported_questions())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(labels, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(labels)} draft labels to {args.output}")


if __name__ == "__main__":
    main()
