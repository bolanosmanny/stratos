"""Render the saved citation review without a live database connection."""

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--verdicts",
        type=Path,
        default=Path(__file__).resolve().parent / "audit_verdicts.json",
    )
    args = parser.parse_args()

    results = json.loads(args.results.read_text())
    predictions = results["results"]
    run = "before" if results["summary"]["answer_mode"] == "legacy" else "after"
    verdicts = json.loads(args.verdicts.read_text())[run]
    refusals = set(verdicts["answerable_abstentions"])
    factual_errors = set(verdicts["factual_errors"])
    unsupported_false = set(verdicts["unsupported_false_answers"])
    chunk_failures = verdicts["chunk_citation_failures"]
    quote_failures = verdicts.get("displayed_quote_failures", {})

    lines = [
        f"# SEC answer and citation audit — {run}",
        "",
        "Verdicts are recorded in audit_verdicts.json. They were reviewed by",
        "the same evaluator, not an independent blinded reviewer. Citation",
        "support requires the requested period and scope, not merely a matching",
        "number elsewhere in the filing.",
        "",
    ]
    for row in predictions:
        case_id = row["id"]
        if not row["answerable"]:
            answer_verdict = "False answer" if case_id in unsupported_false else "Correct refusal"
        elif case_id in refusals:
            answer_verdict = "Incorrect refusal"
        elif case_id in factual_errors:
            answer_verdict = "Incorrect answer"
        else:
            answer_verdict = "Correct answer"
        lines.extend([
            f"## {case_id} — {row['ticker']}",
            "",
            f"Question: {row['question']}",
            f"Expected short answer: {row['expected_answer'] or 'unsupported'}",
            f"Gold SEC source: {row['source_url'] or 'none'}",
            f"Gold evidence: {row['evidence_quote'] or 'none'}",
            f"Model answer: {row['answer'] or 'not run'}",
            f"Adjudication: **{answer_verdict}**",
            "",
        ])
        model_excerpts = {
            item["label"]: item["excerpt"]
            for item in row.get("citation_excerpts", [])
        }
        for chunk in row["cited_source_chunks"]:
            label = chunk["label"]
            full_verdict = "unsupported" if label in chunk_failures.get(case_id, []) else "supported"
            quote_verdict = (
                "unsupported" if label in quote_failures.get(case_id, []) else "supported"
            )
            lines.extend([
                f"Citation [{label}] — chunk {chunk['id']} · full chunk **{full_verdict}**"
                + (f" · displayed quote **{quote_verdict}**" if run == "after" else ""),
                f"Source: {chunk['source_url']}",
                f"Model-selected quote: {model_excerpts.get(label, 'none')}",
                f"Full indexed chunk: {chunk['content'].replace(chr(10), ' ').strip()}",
                "",
            ])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines).rstrip() + "\n")
    print(f"Wrote review sheet for {len(predictions)} questions to {args.output}")


if __name__ == "__main__":
    main()
