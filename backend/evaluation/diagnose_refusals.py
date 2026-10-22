"""Diagnose why the current SEC answer path refuses selected questions.

Evaluation-only: captures local Ollama output without changing production
behavior, and records whether the model itself refused or the guard rejected
its answer. Do not use this trace as an accuracy metric.
"""

import argparse
import json
import os
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv
from supabase import create_client

from services import research_answer
from services.evidence import NUMBER, SOURCE_LABEL, _parse_json, _source_quote, verified_answer
from services.retrieval import retrieve_relevant_chunks_hybrid


def rejection_reason(raw: str, matches: list[dict], question: str = "") -> str:
    value = _parse_json(raw)
    if value is None:
        return "invalid_json"
    answer, evidence = value.get("answer"), value.get("evidence")
    if not isinstance(answer, str) or not isinstance(evidence, list):
        return "invalid_structure"
    if answer.strip() == "INSUFFICIENT_EVIDENCE":
        return "model_refused"

    quotes = {}
    for item in evidence:
        if not isinstance(item, dict):
            continue
        label, quote = item.get("label"), item.get("quote")
        if not isinstance(label, int) or not isinstance(quote, str):
            continue
        if not 1 <= label <= len(matches) or len(quote) < 12:
            continue
        source_quote = _source_quote(quote, matches[label - 1]["content"])
        if source_quote is not None:
            quotes[label] = source_quote
    cited = [int(label) for label in SOURCE_LABEL.findall(answer)]
    if not cited:
        if not quotes or len(quotes) > 2:
            return "missing_citation_or_valid_quote"
        cited = sorted(quotes)
    if not set(cited).issubset(quotes):
        return "cited_quote_not_verified"

    claim_numbers = set(NUMBER.findall(SOURCE_LABEL.sub("", answer)))
    question_numbers = set(NUMBER.findall(question))
    quote_numbers = set(NUMBER.findall(" ".join(quotes[label] for label in set(cited))))
    missing_numbers = (claim_numbers - question_numbers) - quote_numbers
    if missing_numbers:
        return "claim_number_absent_from_quote:" + ",".join(sorted(missing_numbers))
    return "accepted"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", required=True, help="Comma-separated question IDs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replay", type=Path, help="Reuse saved raw outputs; no model calls")
    parser.add_argument("--second-pass", action="store_true", help="Try a more explicit evidence prompt")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--model", default="qwen2.5:7b")
    args = parser.parse_args()

    directory = Path(__file__).resolve().parents[1]
    load_dotenv(directory / ".env")
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    labels = json.loads((directory / "evaluation/sec_questions.json").read_text())
    selected = {part.strip() for part in args.ids.split(",")}
    selected_labels = [label for label in labels if label["id"] in selected]
    if {label["id"] for label in selected_labels} != selected:
        parser.error("Unknown question ID")

    traces = []
    replay = (
        {row["id"]: row["raw_model_output"] for row in json.loads(args.replay.read_text())}
        if args.replay else {}
    )
    if args.replay and selected - set(replay):
        parser.error("Replay file is missing a selected question ID")
    original_chat = research_answer.chat_with_ollama
    for label in selected_labels:
        matches = retrieve_relevant_chunks_hybrid(
            label["ticker"], label["question"], supabase
        )
        if args.replay:
            raw = replay[label["id"]]
            answer, _, _ = verified_answer(raw, matches, label["question"])
            response = {"answer": answer}
        else:
            capture = {}

            def capture_chat(messages, base_url, model):
                if args.second_pass:
                    messages = [dict(message) for message in messages]
                    messages[0]["content"] += (
                        " Before declining, search every excerpt for a direct answer."
                        " For a table, copy one contiguous source span containing"
                        " its header and the relevant row; never stitch together"
                        " nonadjacent words. For a security listing, copy the exact"
                        " note or security and maturity from the same row."
                        " If a precise answer is present, answer it with the quote;"
                        " otherwise return INSUFFICIENT_EVIDENCE."
                    )
                capture["raw"] = original_chat(messages, base_url, model)
                return capture["raw"]

            with (
                patch.object(research_answer, "retrieve_relevant_chunks_hybrid", return_value=matches),
                patch.object(research_answer, "chat_with_ollama", side_effect=capture_chat),
            ):
                response = research_answer.answer_research_question(
                    label["ticker"], label["question"], supabase,
                    args.ollama_url, args.model,
                )
            raw = capture["raw"]
        reason = rejection_reason(raw, matches, label["question"])
        traces.append({
            "id": label["id"],
            "gold_chunk_retrieved": label["gold_chunk_id"] in [row["id"] for row in matches],
            "retrieved_ids": [row["id"] for row in matches],
            "reason": reason,
            "answer": response["answer"],
            "raw_model_output": raw,
        })
        print(f"{label['id']}: {reason}", flush=True)

    args.output.write_text(json.dumps(traces, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(traces)} diagnostic traces to {args.output}")


if __name__ == "__main__":
    main()
