import json
from collections import Counter
from pathlib import Path


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
