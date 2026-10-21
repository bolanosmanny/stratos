"""Create a human-review sheet for saved answer predictions and cited chunks."""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])
    predictions = json.loads(args.results.read_text())["results"]
    cited_ids = {
        row.get("retrieved_top_five", row.get("vector_top_five"))[label - 1]
        for row in predictions
        for label in row["cited_labels"]
        if label <= len(row.get("retrieved_top_five", row.get("vector_top_five")))
    }
    chunks = {}
    ids = sorted(cited_ids)
    for start in range(0, len(ids), 100):
        page = (
            supabase.table("document_chunks")
            .select("id,content,source_url,filing_type,section")
            .in_("id", ids[start : start + 100])
            .execute()
            .data
        )
        chunks.update({item["id"]: item for item in page})

    lines = [
        "# Manual answer and citation audit",
        "",
        "For each supported answer, mark factual correctness and whether each",
        "cited excerpt directly supports the whole claim. The automatic source",
        "quote and numeric checks are not semantic entailment.",
        "",
    ]
    for row in predictions:
        lines.extend([
            f"## {row['id']} — {row['ticker']}",
            "",
            f"Question: {row['question']}",
            f"Expected short answer: {row['expected_answer'] or 'unsupported'}",
            f"Gold SEC source: {row['source_url'] or 'none'}",
            f"Gold evidence: {row['evidence_quote'] or 'none'}",
            f"Model answer: {row['answer'] or 'not run'}",
            "Factual answer correct? [ ] Yes [ ] No [ ] Abstained",
            "Cited claims fully supported? [ ] Yes [ ] No [ ] No citation",
            "",
        ])
        ranking = row.get("retrieved_top_five", row.get("vector_top_five"))
        for label in row["cited_labels"]:
            if label > len(ranking):
                continue
            chunk = chunks.get(ranking[label - 1])
            if chunk is None:
                continue
            lines.extend([
                f"Citation [{label}] — chunk {chunk['id']} · {chunk['filing_type']} · {chunk['section']}",
                f"Source: {chunk['source_url']}",
                f"Excerpt: {chunk['content'][:1400].replace(chr(10), ' ')}",
                "",
            ])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n")
    print(f"Wrote review sheet for {len(predictions)} questions to {args.output}")


if __name__ == "__main__":
    main()
