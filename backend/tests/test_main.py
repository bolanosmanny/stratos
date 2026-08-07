import pytest
import requests
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

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
    main.RESEARCH_REQUESTS.clear()
    monkeypatch.setattr(main, "RESEARCH_RATE_LIMIT", 2)

    request = Request(
        {
            "type": "http",
            "client": ("127.0.0.1", 12345),
            "headers": [],
        }
    )

    main.enforce_research_rate_limit(request)
    main.enforce_research_rate_limit(request)

    with pytest.raises(HTTPException) as error:
        main.enforce_research_rate_limit(request)

    assert error.value.status_code == 429   

def test_stock_news_uses_cache(monkeypatch):
    main.NEWS_CACHE.clear()
    monkeypatch.setattr(main, "ALPHA_VANTAGE_API_KEY", "test_key")

    provider_calls = []

    def fake_get_company_news(symbol, api_key, company_name):
        provider_calls.append((symbol, api_key, company_name))
        return [{"title": "Test article"}]

    monkeypatch.setattr(
        main,
        "get_company_news",
        fake_get_company_news
    )

    first_response = client.get(
        "/stock/aapl/news",
        params={"company_name": "Apple Inc."},
    )
    second_response = client.get(
        "/stock/aapl/news",
        params={"company_name": "Apple Inc."},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(provider_calls) == 1
    assert second_response.json() ["articles"] == [{"title": "Test article"}]

def test_production_ingestion_requires_admin_token(monkeypatch):
    monkeypatch.setattr(main, "APP_ENV", "production")
    monkeypatch.setattr(main, "INGEST_ADMIN_TOKEN", "test-admin-token")

    response = client.post("/research/ingest/AAPL")

    assert response.status_code == 403
    assert response.json() ["detail"] == (
        "Ingestion is disabled for public requests"
    )
