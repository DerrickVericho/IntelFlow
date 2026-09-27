"""Public HTTP behavior, including JSON fields and safe failure responses."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from src.backend.exceptions.cache import CacheUnavailable
from src.backend.exceptions.sectors import SectorsNotFoundError, SectorsUpstreamError
from src.backend.tests.conftest import Harness


ENVELOPE = {"symbol", "as_of", "status", "missing_inputs", "sources"}
SOURCE = {
    "key", "provider", "as_of", "period", "fetched_at",
    "effective_start", "effective_end", "is_stale",
}


def assert_envelope(body: dict[str, object], extra: set[str]) -> None:
    assert set(body) == ENVELOPE | extra
    assert body["symbol"] == "TEST"
    assert body["status"] in {"complete", "partial", "stale"}
    assert isinstance(body["missing_inputs"], list)
    assert isinstance(body["sources"], list)
    assert all(set(source) == SOURCE for source in body["sources"])
    if body["as_of"] is not None:
        date.fromisoformat(body["as_of"])


def assert_error(response: object, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    assert body["error"]["request_id"] == response.headers["X-Request-ID"]


def test_intel_score_response_contract(client: TestClient, harness: Harness) -> None:
    response = client.get("/api/v1/stocks/test.jk/intel-score")
    assert response.status_code == 200, response.text
    body = response.json()
    assert_envelope(body, {"company", "scores", "key_points", "flow", "fundamentals"})
    assert set(body["company"]) == {
        "name", "sector", "sub_sector", "last_close_idr", "close_date",
        "previous_close_idr", "previous_close_date", "change_idr", "change_percent",
    }
    assert body["company"]["close_date"] == body["as_of"]
    assert all(
        set(point) == {"kind", "category", "title", "text", "items", "source_keys"}
        for point in body["key_points"]
    )
    assert set(body["scores"]) == {
        "flow", "fundamental", "combined", "calculation_version",
        "calculated_at", "input_periods", "research_state",
    }
    for name in ("flow", "fundamental", "combined"):
        assert set(body["scores"][name]) == {"value", "reason", "components"}
        assert body["scores"][name]["value"] is not None
        assert all(
            set(component) == {"key", "value", "weight", "reason", "source_keys"}
            for component in body["scores"][name]["components"]
        )
    assert set(body["flow"]) == {
        "window", "effective_start", "effective_end", "trading_days",
        "incomplete_history", "broker_summary", "broker_summary_5d", "foreign_broker_balance", "foreign_flow", "liquidity",
    }
    assert body["flow"]["window"] == "20d"
    assert body["flow"]["trading_days"] == 20
    assert len(body["flow"]["liquidity"]["series"]) == 20
    assert set(body["fundamentals"]) == {"reporting_period", "currency", "groups"}
    assert {group["key"] for group in body["fundamentals"]["groups"]} == {
        "growth", "earnings", "cash_flow", "valuation"
    }
    source_keys = {source["key"] for source in body["sources"]}
    assert all(set(point["source_keys"]) <= source_keys for point in body["key_points"])
    assert harness.transport.calls["get_daily"] == 1


@pytest.mark.parametrize("window,count", [("1d", 1), ("5d", 5), ("20d", 20)])
def test_flow_response_contract(client: TestClient, window: str, count: int) -> None:
    response = client.get(f"/api/v1/stocks/TEST/flow?window={window}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert_envelope(body, {"flow"})
    flow = body["flow"]
    assert flow["window"] == window
    assert flow["trading_days"] == count
    assert len(flow["foreign_flow"]["series"]) == count
    assert len(flow["liquidity"]["series"]) == count
    assert set(flow["broker_summary"]) == {"brokers", "breadth", "daily"}
    assert len(flow["broker_summary"]["daily"]) == (20 if window == "20d" else 0)
    assert (flow["broker_summary_5d"] is not None) == (window == "20d")
    if flow["broker_summary_5d"]:
        assert len(flow["broker_summary_5d"]["daily"]) == 5


def test_price_history_response_contract(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/TEST/price-history?range=1m")
    assert response.status_code == 200, response.text
    body = response.json()
    assert_envelope(body, {"range", "effective_start", "effective_end", "incomplete_history", "series"})
    assert body["range"] == "1m"
    assert body["series"]
    assert set(body["series"][0]) == {"date", "open", "high", "low", "close", "volume", "market_cap"}
    assert body["series"][-1]["date"] == body["as_of"]


def test_shareholders_response_contract(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/TEST/shareholders?year=2026")
    assert response.status_code == 200, response.text
    body = response.json()
    assert_envelope(body, {"year", "supported_years", "categories", "series"})
    assert body["year"] == 2026
    assert set(body["categories"][0]) == {"key", "label"}
    assert set(body["series"][0]) == {
        "date", "shares_number", "holdings", "total_local", "total_foreign",
        "shareholder_count", "shareholder_count_change",
    }
    assert "individual_l" in body["series"][0]["holdings"]
    assert "individual_f" in body["series"][0]["holdings"]


def test_shareholder_year_without_dataset_returns_empty_contract(
    client: TestClient, harness: Harness
) -> None:
    harness.transport.failures["get_shareholder_composition"] = SectorsNotFoundError(
        "private provider detail"
    )
    response = client.get("/api/v1/stocks/TEST/shareholders?year=2025")
    assert response.status_code == 200
    body = response.json()
    assert body["year"] == 2025
    assert body["series"] == []
    assert body["status"] == "partial"
    assert "private provider detail" not in response.text


def test_historical_null_shareholder_count_is_public_null(
    client: TestClient, harness: Harness
) -> None:
    original = harness.transport._get_shareholder_composition

    def with_missing_counts(year: int) -> dict:
        payload = original(year)
        payload["data"][0]["numbers_of_shareholders"] = None
        payload["data"][0]["change_in_shareholders"] = None
        return payload

    harness.transport._get_shareholder_composition = with_missing_counts
    response = client.get("/api/v1/stocks/TEST/shareholders?year=2025")
    assert response.status_code == 200
    body = response.json()
    assert body["series"][0]["shareholder_count"] is None
    assert body["series"][0]["shareholder_count_change"] is None
    assert body["series"][0]["holdings"]["individual_l"] == 100


def test_broker_series_response_contract(client: TestClient) -> None:
    response = client.get("/api/v1/stocks/TEST/broker-series?range=1w&brokers=B0")
    assert response.status_code == 200, response.text
    body = response.json()
    assert_envelope(body, {
        "range", "effective_start", "effective_end", "incomplete_history",
        "default_brokers", "selected_brokers", "available_brokers", "series",
    })
    assert body["selected_brokers"] == ["B0"]
    assert body["series"][0]["broker_code"] == "B0"
    assert set(body["series"][0]["points"][0]) == {
        "date", "buy_idr", "sell_idr", "net_idr", "cumulative_net_idr"
    }


@pytest.mark.parametrize(
    "path,status,code",
    [
        ("/api/v1/stocks/ABC/intel-score", 422, "INVALID_SYMBOL"),
        ("/api/v1/stocks/TEST/flow", 422, "INVALID_REQUEST"),
        ("/api/v1/stocks/TEST/flow?window=8d", 422, "INVALID_REQUEST"),
        ("/api/v1/stocks/TEST/price-history?range=2y", 422, "INVALID_REQUEST"),
        ("/api/v1/stocks/TEST/shareholders?year=2020", 422, "INVALID_YEAR"),
        ("/api/v1/stocks/TEST/broker-series?range=1w&brokers=", 422, "INVALID_BROKERS"),
    ],
)
def test_invalid_request_is_safe_and_uses_no_provider(
    client: TestClient, harness: Harness, path: str, status: int, code: str
) -> None:
    assert_error(client.get(path), status, code)
    assert harness.transport.calls == {}


@pytest.mark.parametrize(
    "failure,status,code",
    [
        (SectorsNotFoundError("private upstream details"), 404, "DATA_NOT_FOUND"),
        (SectorsUpstreamError("private upstream details"), 503, "UPSTREAM_UNAVAILABLE"),
    ],
)
def test_required_provider_failure_returns_public_error(
    client: TestClient, harness: Harness, failure: Exception, status: int, code: str
) -> None:
    harness.transport.failures["get_daily"] = failure
    response = client.get("/api/v1/stocks/TEST/intel-score")
    assert_error(response, status, code)
    assert "private upstream details" not in response.text


def test_empty_required_dataset_returns_404(client: TestClient, harness: Harness) -> None:
    harness.transport.rows = []
    assert_error(client.get("/api/v1/stocks/TEST/intel-score"), 404, "DATA_NOT_FOUND")


def test_optional_provider_failure_returns_partial_json(
    client: TestClient, harness: Harness
) -> None:
    harness.transport.failures["get_foreign_flow"] = SectorsUpstreamError("private detail")
    response = client.get("/api/v1/stocks/TEST/intel-score")
    assert response.status_code == 200
    body = response.json()
    assert_envelope(body, {"company", "scores", "key_points", "flow", "fundamentals"})
    assert body["status"] == "partial"
    assert body["scores"]["flow"]["value"] is None
    assert body["scores"]["fundamental"]["value"] is not None
    assert body["flow"]["foreign_flow"]["net_inflow_idr"] is None
    assert "foreign_flow" in {item["key"] for item in body["missing_inputs"]}
    assert "private detail" not in response.text


def test_cache_failure_returns_503_without_paid_call(client: TestClient, harness: Harness) -> None:
    async def unavailable(_key: str) -> str | None:
        raise CacheUnavailable("private cache details")

    harness.cache.get = unavailable
    response = client.get("/api/v1/stocks/TEST/intel-score")
    assert_error(response, 503, "CACHE_UNAVAILABLE")
    assert "private cache details" not in response.text
    assert harness.transport.calls == {}


def test_unexpected_failure_returns_safe_json(client: TestClient, harness: Harness) -> None:
    harness.transport.failures["get_daily"] = RuntimeError("private internal details")
    response = client.get("/api/v1/stocks/TEST/intel-score")
    assert_error(response, 500, "INTERNAL_ERROR")
    assert "private internal details" not in response.text


def test_health_and_openapi_are_public_without_provider_call(
    client: TestClient, harness: Harness
) -> None:
    assert client.get("/health").json() == {
        "status": "healthy", "dependencies": {"redis": "test-double"}
    }
    schema = client.get("/openapi.json").json()
    assert "/api/v1/stocks/{symbol}/intel-score" in schema["paths"]
    assert harness.transport.calls == {}


def test_health_reports_real_redis_status(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.backend.main as main

    redis = AsyncMock()
    transport = Mock()
    monkeypatch.setattr(main, "create_redis_client", lambda _settings: redis)
    monkeypatch.setattr(main, "SectorsClient", lambda: transport)
    with TestClient(main.create_app()) as actual_client:
        assert actual_client.get("/health").json() == {
            "status": "healthy", "dependencies": {"redis": "healthy"}
        }
        redis.ping.side_effect = RedisConnectionError("private detail")
        response = actual_client.get("/health")
        assert response.status_code == 503
        assert response.json() == {
            "status": "unhealthy", "dependencies": {"redis": "unavailable"}
        }
        assert "private detail" not in response.text
    redis.aclose.assert_awaited_once()
    transport.close.assert_called_once()
