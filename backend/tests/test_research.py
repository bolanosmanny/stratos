import services.research_answer as research_answer
import services.retrieval as retrieval
from services.evidence import verified_answer

def test_research_answer_fallback_without_matches(monkeypatch):
    monkeypatch.setattr(
        research_answer,
        "retrieve_relevant_chunks_hybrid",
        lambda *_args: [],
    )

    result = research_answer.answer_research_question(
        "aapl",
        "What risks does Apple mention?",
        object(),
        "http://ollama:11434",
        "qwen2.5:3b",
    )

    assert result == { 
        "answer": (
            "Sparky could not find indexed SEC filing material for "
            "AAPL yet."
        ),
        "citations": [],
    }

def test_research_answer_builds_citations_from_retrieved_chunks(monkeypatch):
    matches = [
        {
            "filing_type" : "10-Q",
            "section" : "Risk Factors",
            "filing_date" : "2026-05-01",
            "source_url" : "https://example.com/filing",
            "content" : "Supply constraints may affect product availability.",
        }
    ]
    captured = {}

    monkeypatch.setattr(
        research_answer,
        "retrieve_relevant_chunks_hybrid",
        lambda *_args: matches,
    )

    def fake_chat(messages, base_url, model):
        captured["messages"] = messages
        captured["base_url"] = base_url
        captured["model"] = model
        return (
            '{"answer":"Supply constraints may affect product availability. [1]",'
            '"evidence":[{"label":1,"quote":"Supply constraints may affect '
            'product availability."}]}'
        )

    monkeypatch.setattr(research_answer, "chat_with_ollama", fake_chat)

    result = research_answer.answer_research_question(
        "aapl",
        "What supply risks does Apple mention?",
        object(),
        "http://ollama:11434",
        "qwen2.5:3b",
    )

    assert result["answer"] == (
        "Supply constraints may affect product availability. [1]"
    )
    assert result["citations"][0]["label"] == 1
    assert result["citations"][0]["filing_type"] == "10-Q"
    assert "Company ticker: AAPL" in captured["messages"][1]["content"]
    assert captured["model"] == "qwen2.5:3b"


def test_research_answer_refuses_unverifiable_quote(monkeypatch):
    matches = [{
        "filing_type": "10-K", "section": "Risk Factors",
        "filing_date": "2026-01-01", "source_url": "https://example.com/filing",
        "content": "Cash flow was $100 million.",
    }]
    monkeypatch.setattr(
        research_answer, "retrieve_relevant_chunks_hybrid", lambda *_args: matches,
    )
    monkeypatch.setattr(
        research_answer, "chat_with_ollama", lambda *_args:
        '{"answer":"Cash flow was $900 million. [1]",'
        '"evidence":[{"label":1,"quote":"Cash flow was $100 million."}]}',
    )

    result = research_answer.answer_research_question(
        "AAPL", "What was cash flow?", object(), "http://ollama:11434", "qwen2.5:7b",
    )

    assert "do not support" in result["answer"]
    assert result["citations"] == []


def test_evidence_validator_attaches_label_to_verified_quote():
    source = "The company reported cash flow of $281 million in 2025."
    raw = (
        '{"answer":"Cash flow was $281 million in 2025.",'
        '"evidence":[{"label":1,"quote":"reported cash flow of '
        '$281 million in 2025."}]}'
    )

    answer, labels, quotes = verified_answer(raw, [{"content": source}])

    assert answer.endswith("[1]")
    assert labels == [1]
    assert quotes == {1: "reported cash flow of $281 million in 2025."}


def test_evidence_validator_rejects_unrelated_quote():
    raw = (
        '{"answer":"Cash flow was $281 million.",'
        '"evidence":[{"label":1,"quote":"A different filing reported '
        'cash flow of $281 million."}]}'
    )

    answer, labels, quotes = verified_answer(raw, [{"content": "Inventory increased."}])

    assert "do not support" in answer
    assert labels == []
    assert quotes == {}


def test_evidence_validator_uses_valid_quote_when_an_extra_quote_is_wrong():
    raw = (
        '{"answer":"Operating cash flow came from membership fees.",'
        '"evidence":[{"label":1,"quote":"Unrelated fabricated evidence."},'
        '{"label":2,"quote":"Operating cash flow came from membership fees."}]}'
    )
    matches = [
        {"content": "Unrelated source."},
        {"content": "Operating cash flow came from membership fees."},
    ]

    answer, labels, quotes = verified_answer(raw, matches)

    assert answer.endswith("[2]")
    assert labels == [2]
    assert quotes == {2: "Operating cash flow came from membership fees."}

def test_retrieval_uses_ticker_filter_and_query_embedding(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        retrieval,
        "create_embeddings",
        lambda _texts: [[0.1, 0.2, 0.3]],
    )

    class FakeResponse:
        data = [{"content": "Relevant filing excerpt"}]

    class FakeQuery:
        def execute(self):
            return FakeResponse()

    class FakeSupabase:
        def rpc(self, function_name, parameters):
            captured["function_name"] = function_name
            captured["parameters"] = parameters
            return FakeQuery()

    result = retrieval.retrieve_relevant_chunks(
        "aapl",
        "What are the risks?",
        FakeSupabase(),
    )

    assert result == [{"content": "Relevant filing excerpt"}]
    assert captured["function_name"] == "match_document_chunks"
    assert captured["parameters"]["filter_ticker"] == "AAPL"
    assert captured["parameters"]["query_embedding"] == [0.1, 0.2, 0.3]


def test_hybrid_retrieval_fuses_semantic_and_keyword_candidates(monkeypatch):
    vector = [
        {"id": 1, "content": "generic technology risk"},
        {"id": 2, "content": "cash flow overview"},
        {"id": 3, "content": "capital spending summary"},
    ]
    lexical = [
        {"id": 2, "content": "cash capital spending was 128 billion"},
        {"id": 4, "content": "cash capital spending increased"},
    ]
    monkeypatch.setattr(
        retrieval, "retrieve_relevant_chunks", lambda *_args: vector,
    )
    monkeypatch.setattr(
        retrieval, "_ticker_chunks", lambda *_args: lexical,
    )

    result = retrieval.retrieve_relevant_chunks_hybrid(
        "AMZN", "What was cash capital spending?", object(), match_count=3,
    )

    assert result[0]["id"] == 2
    assert len(result) == 3
