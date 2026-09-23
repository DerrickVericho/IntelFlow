import asyncio
import json
import logging
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient

from src.backend.config import Settings
from src.backend.cache.store import MemoryCache, RedisCache
from src.backend.exceptions.cache import CacheUnavailable
from src.backend.exceptions.research import InvalidSymbolError
from src.backend.exceptions.sectors import (
    SectorsResponseError,
    SectorsUpstreamError,
    SectorsValidationError,
)
from src.backend.sectors.cached import (
    CachedSectorsGateway,
    ADAPTERS,
    canonical_key,
    ttl_for,
)
from src.backend.sectors.client import SectorsClient
from src.backend.sectors.dates import latest_provider_date
from src.backend.sectors.mapper import (
    fundamentals_evidence,
    liquidity_evidence,
    broker_evidence,
)
from src.backend.main import create_app
from src.backend.services.research import ResearchService
from src.backend.scoring.research import calculate
from src.backend.logger import JsonFormatter, TextFormatter
from src.backend.tests.fixtures import FixtureTransport, TODAY

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def setup():
    raw, cache = FixtureTransport(), MemoryCache()
    gateway = CachedSectorsGateway(raw, cache, Settings.from_env())
    return raw, cache, gateway, ResearchService(gateway, today=lambda: TODAY)


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize(
    "file,operation",
    [
        ("TransactionData_DailyTransaction.txt", "get_daily"),
        ("CompanyScreener_FreeFloat.txt", "get_free_float"),
        ("Brokers_BrokersActivityPerSymbol.txt", "get_broker_summary"),
        ("Brokers_TopBuyersAndSellers.txt", "get_top_brokers"),
        ("Brokers_ForeignFlow.txt", "get_foreign_flow"),
        ("DetailedReports_Report.txt", "get_company_report"),
        ("DetailedReports_Report_BBCA.txt", "get_company_report"),
        ("DetailedReprots_Shareholder.txt", "get_shareholder_composition"),
        ("DetailedReports_GetSegments.txt", "get_revenue_segments"),
    ],
)
def test_actual_provider_samples(file, operation):
    path = PROJECT_ROOT / "output-schema" / file
    if not path.exists():
        pytest.skip("User-local provider sample not present in this checkout")
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, dict):
        raw["unknown_future_field"] = {"ignored": True}
    assert ADAPTERS[operation].validate_python(raw) is not None


def test_research_has_numeric_arrays_and_sources():
    raw, cache, gateway, service = setup()
    with TestClient(create_app(service=service)) as client:
        result = client.get("/api/v1/stocks/test.jk/intel-score")
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["symbol"] == "TEST"
        assert body["scores"]["combined"]["value"] is not None
        assert len(body["flow"]["liquidity"]["series"]) == 20
        assert len(body["flow"]["foreign_flow"]["series"]) == 20
        assert len(body["flow"]["broker_summary"]["brokers"]) == 20
        assert all(g["metrics"] for g in body["fundamentals"]["groups"])
        assert all(
            m["series"]
            for g in body["fundamentals"]["groups"]
            for m in g["metrics"]
            if m["period_type"] == "annual"
        )
        source_keys = {s["key"] for s in body["sources"]}
        assert all(set(p["source_keys"]) <= source_keys for p in body["key_points"])
        counts = raw.calls.copy()
        second = client.get("/api/v1/stocks/TEST/intel-score").json()
        assert raw.calls == counts
        assert second["scores"]["combined"] == body["scores"]["combined"]
        flow = client.get("/api/v1/stocks/TEST/flow?window=5d").json()
        assert len(flow["flow"]["liquidity"]["series"]) == 5
        assert raw.calls["get_company_report"] == 3
        assert raw.calls["get_daily"] == 1
        assert client.get("/health").status_code == 200
        schema = client.get("/openapi.json").json()
        assert "LiquidityPoint" in schema["components"]["schemas"]


@pytest.mark.parametrize(
    "path,status",
    [
        ("/api/v1/stocks/NOPE/intel-score", 404),
        ("/api/v1/stocks/INVALID/intel-score", 422),
        ("/api/v1/stocks/ABC/intel-score", 422),
        ("/api/v1/stocks/AB1D/intel-score", 422),
        ("/api/v1/stocks/TEST/flow?window=8d", 422),
        ("/api/v1/stocks/TEST/price-history?range=2y", 422),
        ("/api/v1/stocks/TEST/shareholders?year=2099", 422),
        ("/api/v1/stocks/TEST/shareholders?year=2020", 422),
        ("/api/v1/stocks/TEST/broker-series?range=1w&brokers=", 422),
        ("/api/v1/stocks/B!CA/intel-score", 422),
    ],
)
def test_validation_and_errors(path, status):
    raw, _, _, service = setup()
    with TestClient(create_app(service=service)) as client:
        response = client.get(path)
        assert response.status_code == status
        assert (
            response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
        )


@pytest.mark.parametrize("symbol", ["ABC", "ABCDE", "AB1D", "B!CA"])
def test_malformed_symbol_stops_before_provider_call(symbol):
    raw, _, _, service = setup()
    with TestClient(create_app(service=service)) as client:
        response = client.get(f"/api/v1/stocks/{symbol}/intel-score")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == InvalidSymbolError.code
    assert raw.calls == {}

    session = Mock()
    session.headers = {}
    with pytest.raises(Exception):
        SectorsClient("test-key", session=session).get_daily(symbol)
    session.get.assert_not_called()


def test_partial_flow_failure_keeps_fundamentals():
    raw, _, _, service = setup()
    raw.failures["get_foreign_flow"] = SectorsUpstreamError("Timeout")
    response = run(service.research("TEST"))
    assert response.status == "partial"
    assert response.scores.flow.value is None
    assert response.scores.combined.value is None
    assert response.scores.combined.components[0].value is None
    assert response.scores.fundamental.value is not None
    assert response.flow.foreign_flow.net_inflow_idr is None


def test_empty_daily_history_and_upstream_failure():
    raw, _, _, service = setup()
    raw.rows = []
    with TestClient(create_app(service=service)) as client:
        assert client.get("/api/v1/stocks/TEST/intel-score").status_code == 404
    raw.failures["get_daily"] = SectorsUpstreamError("Offline")
    _, _, _, service2 = setup()
    service2.gateway.transport = raw
    with TestClient(create_app(service=service2)) as client:
        assert client.get("/api/v1/stocks/TEST/intel-score").status_code == 503


def test_short_history_never_scores_full_window():
    raw, _, _, service = setup()
    raw.rows = raw.rows[-5:]
    response = run(service.research("TEST"))
    assert response.flow.incomplete_history
    assert response.scores.flow.value is None
    assert all(p.volume_ratio is None for p in response.flow.liquidity.series)


def test_zero_volume_baseline_and_foreign_turnover():
    raw, _, gateway, service = setup()
    for row in raw.rows:
        row["volume"] = 0
    response = run(service.research("TEST"))
    assert response.flow.liquidity.latest_vs_average_ratio is None
    assert response.scores.flow.value is None


def test_nice_to_have_chart_endpoints_and_chunk_cache():
    raw, _, _, service = setup()
    with TestClient(create_app(service=service)) as client:
        price = client.get("/api/v1/stocks/TEST/price-history?range=1m").json()
        assert price["series"][0]["date"] >= (TODAY - timedelta(days=29)).isoformat()
        holders = client.get("/api/v1/stocks/TEST/shareholders?year=2026").json()
        assert len(holders["categories"]) == 18
        assert "supported_years" in holders
        broker = client.get("/api/v1/stocks/TEST/broker-series?range=3m").json()
        assert len(broker["default_brokers"]) == 6
        assert raw.calls["get_broker_summary"] == 7
        selected = client.get(
            "/api/v1/stocks/TEST/broker-series?range=3m&brokers=B0"
        ).json()
        assert raw.calls["get_broker_summary"] == 7
        points = selected["series"][0]["points"]
        assert points[-1]["cumulative_net_idr"] == sum(p["net_idr"] for p in points)


def test_cache_raw_retention_corruption_and_coalescing():
    async def scenario():
        raw, cache, gateway, _ = setup()
        raw.rows[0]["unused_upstream_fact"] = "preserved"
        await asyncio.gather(*(gateway.get_daily("test.jk") for _ in range(5)))
        assert raw.calls["get_daily"] == 1
        key = next(iter(cache.values))
        assert "unused_upstream_fact" in cache.values[key][1]
        await cache.set(key, "invalid-json", 60)
        await gateway.get_daily("TEST")
        assert raw.calls["get_daily"] == 2

    run(scenario())


def test_cache_invalid_fresh_data_not_written():
    raw, cache, gateway, _ = setup()
    raw.rows[0].pop("volume")
    with pytest.raises(SectorsResponseError):
        run(gateway.get_daily("TEST"))
    assert not cache.values


def test_cache_fail_closed():
    class FailedCache(MemoryCache):
        async def get(self, key):
            raise CacheUnavailable("Unavailable")

    raw, _, gateway, service = setup()
    gateway.store = FailedCache()
    with TestClient(create_app(service=service)) as client:
        assert client.get("/api/v1/stocks/TEST/intel-score").status_code == 503
    assert not raw.calls


def test_cache_keys_and_ttl():
    a = canonical_key(
        "p", "get_company_report", "bbca.jk", {"sections": ["valuation", "financials"]}
    )
    b = canonical_key(
        "p", "get_company_report", "BBCA", {"sections": ["financials", "valuation"]}
    )
    assert a == b
    assert canonical_key(
        "p", "get_top_brokers", "BBCA", {"start": "2026-09-01"}
    ) != canonical_key("p", "get_top_brokers", "BBCA", {"start": "2026-09-02"})
    s = Settings.from_env()
    assert (
        ttl_for(
            s, "get_company_report", {"sections": ["valuation", "financials"]}, TODAY
        )
        == s.cache_ttl_company_dynamic_seconds
    )
    assert (
        ttl_for(s, "get_shareholder_composition", {"year": 2025}, TODAY) == 90 * 86400
    )
    assert (
        ttl_for(s, "get_daily", {"end": TODAY.isoformat()}, TODAY)
        == s.cache_ttl_market_current_seconds
    )


@pytest.mark.parametrize("status", [400, 401, 404, 429, 500])
def test_client_error_does_not_retry(status):
    session = Mock()
    session.headers = {}
    session.get.return_value.status_code = status
    session.get.return_value.json.return_value = {"sensitive": "hidden"}
    client = SectorsClient("test-key", session=session)
    with pytest.raises(Exception):
        client.get_daily("BBCA")
    assert session.get.call_count == 1


def test_client_timeout():
    session = Mock()
    session.headers = {}
    session.get.side_effect = requests.Timeout()
    with pytest.raises(SectorsUpstreamError):
        SectorsClient("test-key", session=session).get_daily("BBCA")


def test_fundamental_empty_and_negative_ratios():
    raw, _, _, service = setup()
    response = run(service.research("TEST"))
    empty = fundamentals_evidence(None, None)
    score = calculate(response.flow, empty)
    assert score.fundamental.value is None
    assert score.combined.value is None
    financials = (
        ADAPTERS["get_company_report"]
        .validate_python(raw._get_company_report(["financials"]))
        .financials
    )
    valuation = (
        ADAPTERS["get_company_report"]
        .validate_python(raw._get_company_report(["valuation"]))
        .valuation
    )
    for row in valuation.historical_valuation:
        row.pe = row.pb = row.ps = row.pcf = -1
    evidence = fundamentals_evidence(financials, valuation)
    scores = calculate(response.flow, evidence, financials=financials)
    assert scores.fundamental.components[-1].value is None
    assert all(
        m.period_type != "annual" or all("Q" not in p.period for p in m.series)
        for g in evidence.groups
        for m in g.metrics
    )


def test_logger_does_not_serialize_exception_secrets():
    try:
        raise ValueError("API_KEY_SHOULD_NOT_APPEAR")
    except ValueError:
        import sys

        record = logging.LogRecord(
            "test", logging.ERROR, __file__, 1, "Safe message", (), sys.exc_info()
        )
    text = JsonFormatter().format(record)
    assert "API_KEY_SHOULD_NOT_APPEAR" not in text
    assert json.loads(text)["error_type"] == "ValueError"


def test_development_formatter_colors_severity():
    record = logging.LogRecord("test", logging.WARNING, __file__, 1, "Careful", (), None)
    output = TextFormatter(color=True).format(record)
    assert "\033[33mWARNING" in output
    assert "\033[0m" in output
    assert "Careful" in output


def test_company_partial_and_zero_denominators():
    raw, _, _, service = setup()
    raw.failures["get_company_report"] = SectorsUpstreamError("Offline")
    response = run(service.research("TEST"))
    assert response.scores.flow.value is not None
    assert response.scores.fundamental.value is None
    assert response.company.name is None
    assert response.status == "partial"


def test_stale_market_inputs_remain_explicit():
    raw, _, _, service = setup()
    raw.rows = raw.rows[:-10]
    response = run(service.research("TEST"))
    assert any(s.is_stale for s in response.sources)
    assert response.status in ("stale", "partial")
    assert response.as_of < TODAY


def test_broker_gaps_do_not_fabricate_cumulative_values():
    raw, _, _, service = setup()
    original = raw._get_broker_summary

    def with_gap(**params):
        data = original(**params)
        if data["data"]:
            data["data"][0]["summary"] = [
                b for b in data["data"][0]["summary"] if b["broker_code"] != "B0"
            ]
        return data

    raw._get_broker_summary = with_gap
    response = run(service.brokers("TEST", "1w", "B0"))
    assert response.status == "partial"
    assert response.series[0].points[0].net_idr is None
    assert all(p.cumulative_net_idr is None for p in response.series[0].points)


def test_rank_filters_are_validated_before_caching():
    raw, cache, gateway, _ = setup()
    original = raw._get_top_brokers

    def wrong(**params):
        data = original(**params)
        data["origin"] = "domestic"
        return data

    raw._get_top_brokers = wrong
    with pytest.raises(SectorsResponseError):
        run(gateway.get_top_brokers("TEST"))
    assert not cache.values


def test_nonfinite_and_wrong_symbol_are_not_cached():
    raw, cache, gateway, _ = setup()
    raw.rows[0]["unknown"] = float("nan")
    with pytest.raises(SectorsResponseError):
        run(gateway.get_daily("TEST"))
    assert not cache.values
    raw.rows[0].pop("unknown")
    raw.rows[0]["symbol"] = "OTHER.JK"
    with pytest.raises(SectorsResponseError):
        run(gateway.get_daily("TEST"))
    assert not cache.values


@pytest.mark.parametrize(
    "environment,formatter",
    [("development", "TextFormatter"), ("production", "JsonFormatter")],
)
def test_console_logging(environment, formatter, monkeypatch, capsys):
    from src.backend.logger import configure_logging, set_client_ip, reset_client_ip

    monkeypatch.setenv("APP_ENV", environment)
    configure_logging()
    handlers = logging.getLogger().handlers
    assert len(handlers) == 1
    assert isinstance(handlers[0], logging.StreamHandler)
    assert type(handlers[0].formatter).__name__ == formatter

    token = set_client_ip("192.0.2.10")
    try:
        logging.info("Console log", extra={"status_code": 200})
    finally:
        reset_client_ip(token)

    output = capsys.readouterr().out
    assert "192.0.2.10" in output
    assert "Console log" in output
    if environment == "production":
        assert json.loads(output)["status_code"] == 200
    else:
        assert "status_code=200" in output


def test_request_log_includes_direct_client_ip(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")
    _, _, _, service = setup()
    with TestClient(create_app(service=service)) as client:
        response = client.get("/api/v1/stocks/ABC/intel-score")
    entries = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    completed = next(entry for entry in entries if entry["message"] == "Request completed")
    assert completed["client_ip"] == "testclient"
    assert completed["request_id"] == response.headers["X-Request-ID"]
    assert completed["status_code"] == 422


def test_default_range_becomes_explicit_cache_key():
    async def scenario():
        from datetime import datetime
        from zoneinfo import ZoneInfo

        raw, cache, gateway, _ = setup()
        now = latest_provider_date(datetime.now(ZoneInfo("Asia/Jakarta")).date())
        await gateway.get_daily("TEST")
        await gateway.get_daily(
            "test.jk", start=(now - timedelta(days=29)).isoformat(), end=now.isoformat()
        )
        assert raw.calls["get_daily"] == 1

    run(scenario())


def test_market_requests_do_not_send_jakarta_tomorrow_to_provider():
    jakarta_today = date(2026, 9, 24)
    utc_today = date(2026, 9, 23)
    assert latest_provider_date(jakarta_today, utc_today) == utc_today

    raw, cache = FixtureTransport(), MemoryCache()
    gateway = CachedSectorsGateway(
        raw, cache, Settings.from_env(), utc_today=lambda: utc_today
    )
    service = ResearchService(
        gateway, today=lambda: jakarta_today, utc_today=lambda: utc_today
    )
    requested = {}
    original_daily = raw._get_daily
    original_foreign = raw._get_foreign_flow

    def daily(**params):
        requested["daily"] = params
        return original_daily(**params)

    def foreign(**params):
        requested["foreign"] = params
        return original_foreign(**params)

    raw._get_daily = daily
    raw._get_foreign_flow = foreign
    run(service.research("TEST"))

    assert requested["daily"] == {
        "start": "2026-06-26",
        "end": "2026-09-23",
    }
    assert requested["foreign"]["end"] == "2026-09-23"
    assert service._range("3m")[1] == utc_today
    run(gateway.get_daily("TEST"))
    assert requested["daily"] == {
        "start": "2026-08-25",
        "end": "2026-09-23",
    }
    previous_calls = raw.calls.copy()
    with pytest.raises(SectorsValidationError):
        run(gateway.get_daily("TEST", start="2026-06-27", end="2026-09-24"))
    assert raw.calls == previous_calls


def test_actual_company_samples_map_without_quarter_fabrication():
    for file in ("DetailedReports_Report.txt", "DetailedReports_Report_BBCA.txt"):
        path = PROJECT_ROOT / "output-schema" / file
        if not path.exists():
            pytest.skip("User-local provider sample unavailable")
        report = ADAPTERS["get_company_report"].validate_json(
            path.read_text(encoding="utf-8-sig")
        )
        evidence = fundamentals_evidence(report.financials, report.valuation)
        assert len(evidence.groups) == 4
        for group in evidence.groups:
            for metric in group.metrics:
                if metric.period_type == "quarterly_yoy_undated":
                    assert metric.period is None and metric.series == []
                else:
                    assert all(p.period.isdigit() for p in metric.series)


def test_conflicting_duplicate_dates_rejected():
    raw, _, _, service = setup()
    raw.rows.append({**raw.rows[-1], "volume": 999})
    with pytest.raises(SectorsResponseError):
        run(service.research("TEST"))


def test_negative_volume_is_not_valid_evidence():
    raw, cache, gateway, _ = setup()
    raw.rows[0]["volume"] = -1
    with pytest.raises(SectorsResponseError):
        run(gateway.get_daily("TEST"))
    assert not cache.values


def test_formula_repeatability_with_identical_timestamp():
    from datetime import datetime, UTC

    _, _, _, service = setup()
    response = run(service.research("TEST"))
    stamp = datetime(2026, 9, 22, tzinfo=UTC)
    a = calculate(response.flow, response.fundamentals, calculated_at=stamp)
    b = calculate(response.flow, response.fundamentals, calculated_at=stamp)
    assert a == b


def test_lifespan_closes_resources_and_health_reports_dependency(monkeypatch):
    from unittest.mock import AsyncMock
    import src.backend.main as main

    redis = AsyncMock()
    transport = Mock()
    monkeypatch.setattr(main, "create_redis_client", lambda settings: redis)
    monkeypatch.setattr(main, "SectorsClient", lambda: transport)
    with TestClient(main.create_app()) as client:
        assert client.get("/health").json()["dependencies"]["redis"] == "healthy"
        from redis.exceptions import ConnectionError

        redis.ping.side_effect = ConnectionError("secret-not-logged")
        assert client.get("/health").status_code == 503
    redis.aclose.assert_awaited_once()
    transport.close.assert_called_once()


def test_startup_requires_redis(monkeypatch):
    from unittest.mock import AsyncMock
    from redis.exceptions import ConnectionError
    import src.backend.main as main

    redis = AsyncMock()
    redis.ping.side_effect = ConnectionError("Unavailable")
    monkeypatch.setattr(main, "create_redis_client", lambda settings: redis)
    with pytest.raises(RuntimeError, match="Redis is required"):
        with TestClient(main.create_app()):
            pass
    redis.aclose.assert_awaited_once()
