import pytest
import requests
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI
from routers.health import create_health_router
import routers.stock_context as stock_context
from routers.stock_context import create_stock_context_router
import routers.research as research_router
from routers.research import create_research_router

import main

client = TestClient(main.app)

def test_root_returns_running_messages():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "App is running"}

def test_fmp_rate_limit_returns_clear_error():
    response = requests.Response()
    response.status_code = 429

    with pytest.raises(HTTPException) as error:
        main.check_fmp_response(response)

    assert error.value.status_code == 429
    assert error.value.detail == (
        "Market-data API limit reached. Please try again later."
    )

def test_research_rate_limit_blocks_extra_requests(monkeypatch):
    monkeypatch.setattr(
        research_router,
        "answer_research_question",
        lambda *_args: {
            "answer": "Test answer [1].",
            "citations": [],
        },
    )

    test_app = FastAPI()
    test_app.include_router(
        create_research_router(
            object(),
            {},
            "http://ollama:11434",
            "qwen2.5:3b",
            "development",
            "",
            2,
            600,
        )
    )
    test_client = TestClient(test_app)

    first_response = test_client.post(
        "/research",
        json={"ticker": "AAPL", "question": "What are the risks?"},
    )
    second_response = test_client.post(
        "/research",
        json={"ticker": "AAPL", "question": "What are the risks?"},
    )
    third_response = test_client.post(
        "/research",
        json={"ticker": "AAPL", "question": "What are the risks?"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert third_response.status_code == 429

def test_stock_news_uses_cache(monkeypatch):
    provider_calls = []

    def fake_get_company_news(symbol, api_key, company_name):
        provider_calls.append((symbol, api_key, company_name))
        return [{"title": "Test article"}]

    monkeypatch.setattr(
        stock_context,
        "get_company_news",
        fake_get_company_news,
    )

    test_app = FastAPI()
    test_app.include_router(
        create_stock_context_router(
            "test-key",
            {},
        )
    )
    test_client = TestClient(test_app)

    first_response = test_client.get(
        "/stock/aapl/news",
        params={"company_name": "Apple Inc."},
    )
    second_response = test_client.get(
        "/stock/AAPL/news",
        params={"company_name": "Apple Inc."},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(provider_calls) == 1
    assert second_response.json()["articles"] == [
        {"title": "Test article"}
    ]

def test_production_ingestion_requires_admin_token():
    test_app = FastAPI()
    test_app.include_router(
        create_research_router(
            object(),
            {},
            "http://ollama:11434",
            "qwen2.5:3b",
            "production",
            "test-admin-token",
            6,
            600,
        )
    )
    test_client = TestClient(test_app)

    response = test_client.post("/research/ingest/AAPL")

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Ingestion is disabled for public requests"
    )

def test_health_reports_supabase_connection():
    class FakeQuery:
        def select(self, *_args, **_kwargs):
            return self

        def limit(self, _count):
            return self

        def execute(self):
            return None

    class FakeSupabase:
        def table(self, _table_name):
            return FakeQuery()

    test_app = FastAPI()
    test_app.include_router(create_health_router(FakeSupabase()))

    response = TestClient(test_app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "dependencies": {
            "supabase": "connected",
        },
    }
    