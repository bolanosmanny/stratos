import json
from copy import deepcopy
from collections import Counter
from pathlib import Path

from evaluation.run_sec_eval import cited_labels
from evaluation.score_audit import score_run


LABELS = Path(__file__).resolve().parents[1] / "evaluation" / "sec_questions.json"


def test_sec_evaluation_labels_are_unique_and_source_anchored():
    questions = json.loads(LABELS.read_text())
    supported = [item for item in questions if item["answerable"]]
    unsupported = [item for item in questions if not item["answerable"]]

    assert len(questions) == 50
    assert len({item["id"] for item in questions}) == 50
    assert len(supported) == 40
    assert len(unsupported) == 10
    assert len({item["ticker"] for item in questions}) >= 10
    assert Counter(item["filing_type"] for item in supported).keys() == {
        "10-K", "10-Q", "8-K · Earnings Release",
    }
    for item in supported:
        assert item["expected_answer"] in item["evidence_quote"]
        assert item["source_url"].startswith("https://www.sec.gov/")
        assert isinstance(item["gold_chunk_id"], int)
    for item in unsupported:
        assert item["expected_answer"] is None
        assert item["gold_chunk_id"] is None


def test_citation_parser_handles_legacy_and_current_label_formats():
    assert cited_labels("Example [1, 2] and [3][2].") == [1, 2, 3]


def test_reviewed_sec_metrics_recount_from_saved_verdicts():
    directory = LABELS.parent
    verdicts = json.loads((directory / "audit_verdicts.json").read_text())
    before = json.loads((directory / "results_before.json").read_text())
    after = json.loads((directory / "results_final.json").read_text())

    assert score_run(before, verdicts["before"])["answerable_factual_correct"] == 31
    improved = score_run(after, verdicts["after"])
    assert improved["answerable_factual_correct"] == 28
    assert improved["chunk_citations_supported"] == 31
    assert improved["displayed_quotes_supporting_claim"] == 26

    invalid = deepcopy(verdicts["after"])
    invalid["chunk_citation_failures"]["S04"] = [1]
    try:
        score_run(after, invalid)
    except AssertionError as error:
        assert "non-printed citation" in str(error)
    else:
        raise AssertionError("Invalid citation verdict should be rejected")
