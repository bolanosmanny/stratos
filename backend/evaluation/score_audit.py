"""Score the recorded, claim-level human verdicts against immutable run outputs.

This does not judge language-model answers automatically: the review decisions
live in audit_verdicts.json. The script checks that every verdict refers to a
real answer/citation and makes all denominators reproducible.
"""

import argparse
import json
from pathlib import Path


def score_run(results: dict, verdicts: dict) -> dict:
    rows = {row["id"]: row for row in results["results"]}
    answerable = {case_id for case_id, row in rows.items() if row["answerable"]}
    unsupported = set(rows) - answerable
    refusals = set(verdicts["answerable_abstentions"])
    factual_errors = set(verdicts["factual_errors"])
    false_unsupported = set(verdicts["unsupported_false_answers"])

    assert len(answerable) == 40 and len(unsupported) == 10
    assert refusals <= answerable
    assert factual_errors <= answerable - refusals
    assert false_unsupported <= unsupported
    assert refusals == {
        case_id for case_id in answerable if rows[case_id]["abstained"]
    }
    assert false_unsupported == {
        case_id for case_id in unsupported if not rows[case_id]["abstained"]
    }

    substantive = answerable - refusals
    printed = {
        (case_id, label)
        for case_id in substantive
        for label in rows[case_id]["cited_labels"]
    }

    def failed_citations(key: str) -> set[tuple[str, int]]:
        failures = {
            (case_id, label)
            for case_id, labels in verdicts.get(key, {}).items()
            for label in labels
        }
        assert failures <= printed, f"{key} contains a non-printed citation"
        return failures

    chunk_failures = failed_citations("chunk_citation_failures")
    quote_failures = failed_citations("displayed_quote_failures")
    if "displayed_quote_failures" in verdicts:
        assert chunk_failures <= quote_failures

    fully_supported = sum(
        bool(rows[case_id]["cited_labels"])
        and all(
            (case_id, label) not in chunk_failures
            for label in rows[case_id]["cited_labels"]
        )
        for case_id in substantive
    )
    output = {
        "answerable_factual_correct": len(answerable) - len(refusals) - len(factual_errors),
        "answerable_total": len(answerable),
        "answerable_abstentions": len(refusals),
        "unsupported_declined": len(unsupported) - len(false_unsupported),
        "unsupported_total": len(unsupported),
        "chunk_citations_supported": len(printed) - len(chunk_failures),
        "printed_citations_on_substantive_answerable_responses": len(printed),
        "substantive_answers_with_all_chunks_supporting_claim": fully_supported,
        "substantive_answerable_responses": len(substantive),
    }
    if "displayed_quote_failures" in verdicts:
        output["displayed_quotes_supporting_claim"] = len(printed) - len(quote_failures)
        output["displayed_quotes_total"] = len(printed)
    return output


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--verdicts", type=Path, default=here / "audit_verdicts.json")
    parser.add_argument("--before", type=Path, default=here / "results_before.json")
    parser.add_argument("--after", type=Path, default=here / "results_final.json")
    parser.add_argument(
        "--single-verdicts", type=Path,
        help="Score one saved run with an after-style verdict file instead of the original pair",
    )
    args = parser.parse_args()

    if args.single_verdicts:
        results = json.loads(args.after.read_text())
        verdicts = json.loads(args.single_verdicts.read_text())
        print(json.dumps(score_run(results, verdicts), indent=2))
        return

    verdicts = json.loads(args.verdicts.read_text())
    before = json.loads(args.before.read_text())
    after = json.loads(args.after.read_text())
    assert [row["id"] for row in before["results"]] == [
        row["id"] for row in after["results"]
    ]
    assert [row["question"] for row in before["results"]] == [
        row["question"] for row in after["results"]
    ]
    print(json.dumps({
        "before": score_run(before, verdicts["before"]),
        "after": score_run(after, verdicts["after"]),
    }, indent=2))


if __name__ == "__main__":
    main()
