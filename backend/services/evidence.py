"""Conservative validation of model-provided filing evidence.

This verifies quote provenance and numeric consistency. It is not a general
natural-language entailment checker; qualitative claims still merit review.
"""

import json
import re
from difflib import SequenceMatcher


SOURCE_LABEL = re.compile(r"\[(\d+)\]")
NUMBER = re.compile(r"\b\d[\d,.]*%?\b")
REFUSAL = "The indexed SEC filing excerpts do not support an answer to this question."


def _source_quote(quote: str, content: str) -> str | None:
    if quote in content:
        return quote
    # Qwen sometimes omits a few words from a long otherwise verbatim span.
    # Accept only a near-complete contiguous match and use the source's own
    # bytes for subsequent numeric validation, never the model's quote.
    match = SequenceMatcher(None, quote, content, autojunk=False).find_longest_match()
    if match.size / max(len(quote), 1) < 0.90:
        return None
    return content[match.b : match.b + match.size]


def _parse_json(raw: str) -> dict | None:
    text = raw.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    try:
        value = json.loads(text.strip())
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def verified_answer(raw: str, matches: list[dict]) -> tuple[str, list[int], dict[int, str]]:
    """Return answer, cited labels, and exact source quotes, or a refusal."""
    value = _parse_json(raw)
    if value is None:
        return REFUSAL, [], {}
    answer = value.get("answer")
    evidence = value.get("evidence")
    if not isinstance(answer, str) or not isinstance(evidence, list):
        return REFUSAL, [], {}
    answer = answer.strip()
    if answer == "INSUFFICIENT_EVIDENCE":
        return REFUSAL, [], {}

    quotes = {}
    for item in evidence:
        if not isinstance(item, dict):
            continue
        label, quote = item.get("label"), item.get("quote")
        if not isinstance(label, int) or not isinstance(quote, str):
            continue
        if label < 1 or label > len(matches) or len(quote) < 12:
            continue
        source_quote = _source_quote(quote, matches[label - 1]["content"])
        if source_quote is None:
            continue
        quotes[label] = source_quote

    cited = [int(label) for label in SOURCE_LABEL.findall(answer)]
    if not cited:
        # The structured evidence is authoritative when the model forgets to
        # print a label in otherwise valid single-sentence prose.
        if not quotes or len(quotes) > 2:
            return REFUSAL, [], {}
        cited = sorted(quotes)
        answer = f"{answer.rstrip()} {' '.join(f'[{label}]' for label in cited)}"
    if not set(cited).issubset(quotes):
        return REFUSAL, [], {}

    # A citation for an invented amount or year must never pass validation.
    claim_text = SOURCE_LABEL.sub("", answer)
    claim_numbers = set(NUMBER.findall(claim_text))
    evidence_numbers = set(NUMBER.findall(" ".join(quotes[label] for label in set(cited))))
    if not claim_numbers.issubset(evidence_numbers):
        return REFUSAL, [], {}

    labels = sorted(set(cited))
    return answer, labels, {label: quotes[label] for label in labels}
