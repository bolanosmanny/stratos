"""Evaluate current Stratos retrieval and answers against fixed source labels.

The automatic answer/citation checks are deliberately narrow proxies. Review
the saved predictions against source excerpts before claiming factual or
citation accuracy in a resume or public README.
"""

import argparse
import json
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

from services.research_answer import answer_research_question
from services.retrieval import retrieve_relevant_chunks, retrieve_relevant_chunks_hybrid


TOKEN = re.compile(r"[a-z0-9]+")
CITATION = re.compile(r"\[([1-5])\]")
STOP = {"a", "an", "and", "are", "as", "at", "by", "for", "from", "how", "in", "is", "of", "on", "or", "the", "to", "was", "were", "what", "which", "with"}


def tokens(text: str) -> list[str]:
    return [word for word in TOKEN.findall(text.casefold()) if word not in STOP]


def keyword_top_five(question: str, rows: list[dict]) -> list[int]:
    """Small, dependency-free BM25 baseline over the same indexed chunks."""
    terms = tokens(question)
    docs = [Counter(tokens(row["content"])) for row in rows]
    df = Counter(term for doc in docs for term in doc)
    avg_length = sum(sum(doc.values()) for doc in docs) / max(1, len(docs))
    scores = []
    for row, doc in zip(rows, docs):
        length = sum(doc.values())
        score = 0.0
        for term in terms:
            frequency = doc[term]
            if not frequency:
                continue
            idf = math.log(1 + (len(rows) - df[term] + 0.5) / (df[term] + 0.5))
            score += idf * frequency * 2.2 / (
                frequency + 1.2 * (0.25 + 0.75 * length / max(avg_length, 1))
            )
        scores.append((score, row["id"]))
    scores.sort(key=lambda item: (-item[0], item[1]))
    return [chunk_id for _, chunk_id in scores[:5]]


def fetch_corpus(supabase) -> dict[str, list[dict]]:
    rows = []
    for start in range(0, 10000, 1000):
        page = (
            supabase.table("document_chunks")
            .select("id,ticker,content")
            .range(start, start + 999)
            .execute()
            .data
        )
        rows.extend(page)
        if len(page) < 1000:
            break
    by_ticker = defaultdict(list)
    for row in rows:
        by_ticker[row["ticker"]].append(row)
    return by_ticker


def contains_expected(answer: str, expected: str | None) -> bool:
    if not expected:
        return False
    normalized_answer = " ".join(TOKEN.findall(answer.casefold()))
    normalized_expected = " ".join(TOKEN.findall(expected.casefold()))
    return normalized_expected in normalized_answer


def is_abstention(answer: str) -> bool:
    text = answer.casefold()
    return any(phrase in text for phrase in (
        "cannot be determined", "cannot determine", "cannot find",
        "not possible to determine", "do not contain", "does not contain",
        "does not provide", "not mentioned", "no explicit mention",
        "do not support an answer", "insufficient evidence",
        "not available in the provided", "no information regarding",
    ))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=Path("evaluation/sec_questions.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ids", help="Comma-separated case IDs for a focused smoke run")
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--retriever", choices=["vector", "hybrid"], default="vector")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen2.5:7b")
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    corpus = fetch_corpus(supabase)
    labels = json.loads(args.labels.read_text())
    if args.ids:
        selected = {item.strip() for item in args.ids.split(",")}
        labels = [item for item in labels if item["id"] in selected]
    if args.limit:
        labels = labels[: args.limit]
    indexed_ids = {row["id"] for rows in corpus.values() for row in rows}
    missing_gold_ids = [
        label["id"] for label in labels
        if label["answerable"] and label["gold_chunk_id"] not in indexed_ids
    ]
    if missing_gold_ids:
        raise RuntimeError(
            f"Gold chunks were reindexed or removed: {missing_gold_ids}. "
            "Relabel against the current corpus before scoring."
        )
    results = []
    for label in labels:
        retrieve = (
            retrieve_relevant_chunks_hybrid if args.retriever == "hybrid"
            else retrieve_relevant_chunks
        )
        matches = retrieve(label["ticker"], label["question"], supabase)
        retrieved_ids = [match["id"] for match in matches]
        keyword_ids = keyword_top_five(label["question"], corpus[label["ticker"]])
        row = {
            **label,
            "retrieved_top_five": retrieved_ids,
            "keyword_top_five": keyword_ids,
            "retriever_gold_hit": label["gold_chunk_id"] in retrieved_ids if label["answerable"] else None,
            "keyword_gold_hit": label["gold_chunk_id"] in keyword_ids if label["answerable"] else None,
            "max_similarity": matches[0].get("similarity") if matches else None,
            "answer": None,
            "cited_labels": [],
            "citation_excerpts": [],
            "exact_answer_included": None,
            "cites_gold_chunk": None,
            "abstained": None,
        }
        if not args.retrieval_only:
            response = answer_research_question(
                label["ticker"], label["question"], supabase,
                args.ollama_url, args.model,
            )
            answer = response["answer"]
            cited = sorted({int(number) for number in CITATION.findall(answer)})
            row["answer"] = answer
            row["cited_labels"] = cited
            row["citation_excerpts"] = response["citations"]
            row["exact_answer_included"] = (
                contains_expected(answer, label["expected_answer"])
                if label["answerable"] else None
            )
            row["cites_gold_chunk"] = (
                any(retrieved_ids[index - 1] == label["gold_chunk_id"] for index in cited if index <= len(retrieved_ids))
                if label["answerable"] else None
            )
            row["abstained"] = is_abstention(answer)
        results.append(row)
        print(f"{label['id']} {args.retriever}={row['retriever_gold_hit']} keyword={row['keyword_gold_hit']} answer={row['exact_answer_included']} abstained={row['abstained']}", flush=True)

    supported = [row for row in results if row["answerable"]]
    unsupported = [row for row in results if not row["answerable"]]
    summary = {
        "questions": len(results),
        "supported": len(supported),
        "unsupported": len(unsupported),
        "corpus_chunks": sum(len(rows) for rows in corpus.values()),
        "retriever_name": args.retriever,
        "retriever_gold_chunk_recall_at_5": sum(row["retriever_gold_hit"] for row in supported) / max(1, len(supported)),
        "keyword_gold_chunk_recall_at_5": sum(row["keyword_gold_hit"] for row in supported) / max(1, len(supported)),
        "exact_answer_inclusion_rate": (
            sum(row["exact_answer_included"] for row in supported) / max(1, len(supported))
            if not args.retrieval_only else None
        ),
        "gold_chunk_citation_hit_rate": (
            sum(row["cites_gold_chunk"] for row in supported) / max(1, len(supported))
            if not args.retrieval_only else None
        ),
        "unsupported_abstention_rate": (
            sum(row["abstained"] for row in unsupported) / max(1, len(unsupported))
            if not args.retrieval_only else None
        ),
        "label_note": "Source-span-verified labels need independent semantic review; exact answer and gold-chunk citation checks are conservative proxies, not audited factual/citation accuracy.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
