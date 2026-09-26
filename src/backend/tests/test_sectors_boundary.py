"""Sectors request mapping, response validation and cache boundary."""

import asyncio
import json
from typing import Any
from unittest.mock import Mock

import pytest
import requests

from src.backend.exceptions.cache import CacheUnavailable
from src.backend.exceptions.sectors import (
    SectorsAuthenticationError,
    SectorsNotFoundError,
    SectorsRateLimitError,
    SectorsResponseError,
    SectorsUpstreamError,
    SectorsValidationError,
)
from src.backend.sectors.client import SectorsClient
from src.backend.sectors.adapters import ADAPTERS
from src.backend.tests.conftest import Harness
from src.backend.tests.fixtures import FixtureTransport


def test_client_sends_documented_daily_request() -> None:
    session = Mock()
    session.headers = {}
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = [{"symbol": "BBCA.JK"}]
    client = SectorsClient("test-key", session=session)
    result = client.get_daily("bbca.jk", start="2025-05-01", end="2025-05-14")
    assert result == [{"symbol": "BBCA.JK"}]
    session.get.assert_called_once_with(
        "https://api.sectors.app/v2/daily/BBCA/",
        params={"start": "2025-05-01", "end": "2025-05-14"},
        timeout=client.timeout,
    )
    assert session.headers == {"Authorization": "test-key", "Accept": "application/json"}


def test_company_report_sends_only_requested_sections() -> None:
    session = Mock()
    session.headers = {}
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = {}
    SectorsClient("test-key", session=session).get_company_report(
        "BBCA", sections=["financials", "valuation"]
    )
    assert session.get.call_args.args[0].endswith("/company/report/BBCA/")
    assert session.get.call_args.kwargs["params"] == {
        "sections": "financials,valuation"
    }


@pytest.mark.parametrize(
    "method,args,kwargs,path,params",
    [
        ("get_top_brokers", ("BBCA",), {"start": "2025-05-01", "end": "2025-05-14", "foreign": True},
         "broker-summary/BBCA/top/", {"start": "2025-05-01", "end": "2025-05-14", "foreign": "true"}),
        ("get_foreign_flow", ("BBCA",), {"start": "2025-05-01", "end": "2025-05-14"},
         "foreign-flow/BBCA/", {"start": "2025-05-01", "end": "2025-05-14"}),
        ("get_broker_summary", ("BBCA",), {"broker_code": "mg"},
         "broker-summary/BBCA/", {"broker_code": "MG"}),
        ("get_shareholder_composition", ("BBCA",), {"year": 2025},
         "company/shareholders-composition/BBCA/", {"year": 2025}),
        ("get_revenue_segments", ("BBCA",), {"financial_year": 2025},
         "company/get-segments/BBCA/", {"financial_year": 2025}),
        ("get_free_float", (), {"sector": "financials"},
         "free-float/", {"sector": "financials"}),
    ],
)
def test_client_maps_supported_operations(
    method: str, args: tuple[str, ...], kwargs: dict[str, Any],
    path: str, params: dict[str, Any]
) -> None:
    session = Mock()
    session.headers = {}
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = {}
    client = SectorsClient("test-key", session=session)
    getattr(client, method)(*args, **kwargs)
    assert session.get.call_args.args[0] == f"https://api.sectors.app/v2/{path}"
    assert session.get.call_args.kwargs["params"] == params


@pytest.mark.parametrize(
    "operation,payload",
    [
        ("get_daily", lambda raw: raw._get_daily()),
        ("get_free_float", lambda _raw: [{"symbol": "TEST.JK", "company_name": "Test", "free_float": 0.4}]),
        ("get_broker_summary", lambda raw: raw._get_broker_summary(start="2026-09-01", end="2026-09-14")),
        ("get_top_brokers", lambda raw: raw._get_top_brokers(start="2026-09-01", end="2026-09-14")),
        ("get_foreign_flow", lambda raw: raw._get_foreign_flow(start="2026-09-01", end="2026-09-14")),
        ("get_company_report", lambda raw: raw._get_company_report(sections=["overview", "financials", "valuation"])),
        ("get_shareholder_composition", lambda raw: raw._get_shareholder_composition(year=2026)),
        ("get_revenue_segments", lambda _raw: {"symbol": "TEST.JK", "financial_year": 2025,
                                               "revenue_breakdown": [{"value": 100, "source": "Test", "target": "Sales"}]}),
    ],
)
def test_provider_shapes_accept_future_fields_and_require_identity(
    operation: str, payload: Any
) -> None:
    raw = payload(FixtureTransport())
    row = raw[0] if isinstance(raw, list) else raw
    row["future_provider_field"] = "ignored"
    parsed = ADAPTERS[operation].validate_python(raw)
    parsed_row = parsed[0] if isinstance(parsed, list) else parsed
    assert parsed_row.symbol == "TEST.JK"
    assert not hasattr(parsed_row, "future_provider_field")
    del row["symbol"]
    with pytest.raises(ValueError):
        ADAPTERS[operation].validate_python(raw)


@pytest.mark.parametrize(
    "status,error_type",
    [
        (400, SectorsValidationError),
        (401, SectorsAuthenticationError),
        (403, SectorsAuthenticationError),
        (404, SectorsNotFoundError),
        (429, SectorsRateLimitError),
        (500, SectorsUpstreamError),
    ],
)
def test_client_maps_upstream_errors_without_retry(status: int, error_type: type[Exception]) -> None:
    session = Mock()
    session.headers = {}
    session.get.return_value.status_code = status
    session.get.return_value.json.return_value = {"private": "do-not-expose"}
    with pytest.raises(error_type) as caught:
        SectorsClient("test-key", session=session).get_daily("BBCA")
    assert caught.value.status_code == status
    session.get.assert_called_once()


@pytest.mark.parametrize("failure", [requests.Timeout(), requests.ConnectionError()])
def test_client_network_failure_is_typed(failure: Exception) -> None:
    session = Mock()
    session.headers = {}
    session.get.side_effect = failure
    with pytest.raises(SectorsUpstreamError):
        SectorsClient("test-key", session=session).get_daily("BBCA")
    session.get.assert_called_once()


def test_client_rejects_invalid_symbol_before_request() -> None:
    session = Mock()
    session.headers = {}
    with pytest.raises(SectorsValidationError):
        SectorsClient("test-key", session=session).get_daily("ABC")
    session.get.assert_not_called()


def test_gateway_keeps_raw_unknown_fields_but_exposes_typed_data(harness: Harness) -> None:
    harness.transport.rows[0]["future_provider_field"] = {"new": True}
    first = asyncio.run(harness.gateway.get_daily("TEST"))
    assert not hasattr(first.data[0], "future_provider_field")
    cached = json.loads(next(iter(harness.cache.values.values()))[1])
    assert cached["payload"][0]["future_provider_field"] == {"new": True}
    second = asyncio.run(harness.gateway.get_daily("test.jk"))
    assert second.data == first.data
    assert harness.transport.calls["get_daily"] == 1


@pytest.mark.parametrize("change", ["missing_volume", "wrong_symbol", "negative_volume"])
def test_gateway_rejects_invalid_provider_data_without_caching(
    harness: Harness, change: str
) -> None:
    if change == "missing_volume":
        harness.transport.rows[0].pop("volume")
    elif change == "wrong_symbol":
        harness.transport.rows[0]["symbol"] = "OTHER.JK"
    else:
        harness.transport.rows[0]["volume"] = -1
    with pytest.raises(SectorsResponseError):
        asyncio.run(harness.gateway.get_daily("TEST"))
    assert harness.cache.values == {}


def test_invalid_cached_payload_is_refetched(harness: Harness) -> None:
    asyncio.run(harness.gateway.get_daily("TEST"))
    key = next(iter(harness.cache.values))
    asyncio.run(harness.cache.set(key, "invalid-json", 60))
    asyncio.run(harness.gateway.get_daily("TEST"))
    assert harness.transport.calls["get_daily"] == 2


def test_cache_write_failure_is_typed(harness: Harness) -> None:
    async def unavailable(_key: str, _value: str, _ttl: int) -> None:
        raise CacheUnavailable("cache is down")

    harness.cache.set = unavailable
    with pytest.raises(CacheUnavailable):
        asyncio.run(harness.gateway.get_daily("TEST"))


def test_provider_request_date_validation_precedes_fetch(harness: Harness) -> None:
    with pytest.raises(SectorsValidationError):
        asyncio.run(harness.gateway.get_daily("TEST", start="2026-09-23", end="2026-09-24"))
    assert harness.transport.calls == {}
