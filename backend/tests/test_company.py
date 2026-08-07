from fastapi import FastAPI
from fastapi.testclient import TestClient

import routers.company as company_router
from routers.company import create_company_router


def create_test_client() -> TestClient:
    test_app = FastAPI()
    test_app.include_router(
        create_company_router("test-fmp-key")
    )
    return TestClient(test_app)


def test_fundamentals_calculate_growth_margin_and_pe(monkeypatch):
    class FakeResponse:
        def __init__(self, data):
            self.status_code = 200
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    def fake_get(url, **_kwargs):
        if url.endswith("/quote"):
            return FakeResponse(
                [{"price": 200, "pe": None, "lastDiv": 0.25}]
            )

        if url.endswith("/income-statement"):
            return FakeResponse(
                [
                    {
                        "date": "2026-06-30",
                        "revenue": 120,
                        "netIncome": 24,
                        "eps": 10,
                        "grossProfit": 60,
                        "operatingIncome": 30,
                        "ebitda": 35,
                    },
                    {"revenue": 100},
                ]
            )

        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(company_router.requests, "get", fake_get)

    response = create_test_client().get(
        "/stock/AAPL/fundamentals"
    )

    assert response.status_code == 200
    assert response.json()["peRatio"] == 20
    assert response.json()["revenueGrowth"] == 20
    assert response.json()["netMargin"] == 20


def test_financial_health_calculates_ratios_and_free_cash_flow(
    monkeypatch,
):
    class FakeResponse:
        def __init__(self, data):
            self.status_code = 200
            self._data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    def fake_get(url, **_kwargs):
        if url.endswith("/balance-sheet-statement"):
            return FakeResponse(
                [
                    {
                        "date": "2026-06-30",
                        "totalCurrentAssets": 300,
                        "totalCurrentLiabilities": 150,
                        "totalDebt": 90,
                        "totalStockholdersEquity": 45,
                        "cashAndCashEquivalents": 50,
                        "totalAssets": 500,
                        "totalLiabilities": 250,
                    }
                ]
            )

        if url.endswith("/cash-flow-statement"):
            return FakeResponse(
                [
                    {
                        "operatingCashFlow": 100,
                        "capitalExpenditure": -15,
                        "freeCashFlow": None,
                    }
                ]
            )

        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(company_router.requests, "get", fake_get)

    response = create_test_client().get(
        "/stock/AAPL/financial-health"
    )

    assert response.status_code == 200
    assert response.json()["currentRatio"] == 2
    assert response.json()["debtToEquity"] == 2
    assert response.json()["freeCashFlow"] == 85
