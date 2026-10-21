"""Reconcile corrected labels and targeted reruns without regenerating 100 answers.

Only label metadata/automatic scores are recomputed. A changed question must
have an override prediction produced by rerunning that exact question.
"""

import argparse
import json
from pathlib import Path

from evaluation.run_sec_eval import contains_expected, is_abstention


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--override", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.base.read_text())
    labels = {item["id"]: item for item in json.loads(args.labels.read_text())}
    overrides = {}
    for path in args.override:
        overrides.update({
            item["id"]: item
            for item in json.loads(path.read_text())["results"]
        })

    rows = []
    for original in payload["results"]:
        case_id = original["id"]
        label = labels[case_id]
        row = {**original, **overrides.get(case_id, {}), **label}
        if original["question"] != label["question"] and case_id not in overrides:
            raise ValueError(f"Changed question needs an override prediction: {case_id}")

        retrieved = row["retrieved_top_five"]
        keyword = row["keyword_top_five"]
        if row["answerable"]:
            gold = row["gold_chunk_id"]
            row["retriever_gold_hit"] = gold in retrieved
            row["keyword_gold_hit"] = gold in keyword
            row["exact_answer_included"] = contains_expected(
                row["answer"], row["expected_answer"]
            )
            row["cites_gold_chunk"] = any(
                retrieved[index - 1] == gold
                for index in row["cited_labels"]
                if 1 <= index <= len(retrieved)
            )
        row["abstained"] = is_abstention(row["answer"])
        rows.append(row)

    supported = [row for row in rows if row["answerable"]]
    unsupported = [row for row in rows if not row["answerable"]]
    summary = payload["summary"]
    summary.update({
        "retriever_gold_chunk_recall_at_5": sum(
            row["retriever_gold_hit"] for row in supported
        ) / len(supported),
        "keyword_gold_chunk_recall_at_5": sum(
            row["keyword_gold_hit"] for row in supported
        ) / len(supported),
        "exact_answer_inclusion_rate": sum(
            row["exact_answer_included"] for row in supported
        ) / len(supported),
        "gold_chunk_citation_hit_rate": sum(
            row["cites_gold_chunk"] for row in supported
        ) / len(supported),
        "unsupported_abstention_rate": sum(
            row["abstained"] for row in unsupported
        ) / len(unsupported),
        "label_note": (
            "Source anchors were verified against the indexed chunks. "
            "Answer-text and gold-chunk citation checks are automatic proxies; "
            "see the claim-level audit for factual and citation correctness."
        ),
    })
    args.output.write_text(
        json.dumps({"summary": summary, "results": rows}, indent=2, ensure_ascii=False)
        + "\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
