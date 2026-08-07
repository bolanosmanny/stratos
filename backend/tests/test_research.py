import services.research_answer as research_answer
import services.retrieval as retrieval

def test_research_answer_fallback_without_matches(monkeypatch):
    monkeypatch.setattr(
        research_answer,
        "retrieve_relevant_chunks",
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
        "retrieve_relevant_chunks",
        lambda *_args: matches,
    )

    def fake_chat(messages, base_url, model):
        captured["messages"] = messages
        captured["base_url"] = base_url
        captured["model"] = model
        return "Supply constraints may affect availability. [1]."

    monkeypatch.setattr(research_answer, "chat_with_ollama", fake_chat)

    result = research_answer.answer_research_question(
        "aapl",
        "What supply risks does Apple mention?",
        object(),
        "http://ollama:11434",
        "qwen2.5:3b",
    )

    assert result["answer"] == (
        "Supply constraints may affect availability. [1]."
    )
    assert result["citations"][0]["label"] == 1
    assert result["citations"][0]["filing_type"] == "10-Q"
    assert "Company ticker: AAPL" in captured["messages"][1]["content"]
    assert captured["model"] == "qwen2.5:3b"

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
