"""Research use cases and failure policy, without asserting score formulas."""

import asyncio
from datetime import date
from typing import Any

import pytest

from src.backend.exceptions.research import InvalidWindowError
from src.backend.exceptions.sectors import SectorsUpstreamError
from src.backend.tests.conftest import Harness


def test_research_returns_provenance_and_reuses_cached_inputs(harness: Harness) -> None:
    first = asyncio.run(harness.service.research("test.jk"))
    assert first.symbol == "TEST"
    assert first.as_of == date(2026, 9, 22)
    assert first.scores.calculation_version
    assert first.scores.input_periods
    assert {source.key for source in first.sources} >= {
        "daily", "broker_top", "foreign_flow", "company_financials", "company_valuation"
    }
    assert all(source.fetched_at.tzinfo is not None for source in first.sources)
    calls = harness.transport.calls.copy()
    second = asyncio.run(harness.service.research("TEST"))
    assert harness.transport.calls == calls
    assert second.scores.calculation_version == first.scores.calculation_version


def test_optional_foreign_failure_keeps_fundamentals(harness: Harness) -> None:
    harness.transport.failures["get_foreign_flow"] = SectorsUpstreamError("offline")
    response = asyncio.run(harness.service.research("TEST"))
    assert response.status == "partial"
    assert response.scores.flow.value is None
    assert response.scores.combined.value is None
    assert response.scores.fundamental.value is not None
    assert response.flow.foreign_flow.net_inflow_idr is None
    assert "foreign_flow" in {item.key for item in response.missing_inputs}
    assert "foreign_flow" not in {source.key for source in response.sources}


def test_optional_company_failure_keeps_flow(harness: Harness) -> None:
    harness.transport.failures["get_company_report"] = SectorsUpstreamError("offline")
    response = asyncio.run(harness.service.research("TEST"))
    assert response.status == "partial"
    assert response.scores.flow.value is not None
    assert response.scores.fundamental.value is None
    assert response.company.name is None
    assert {"company_overview", "company_financials", "company_valuation"} <= {
        item.key for item in response.missing_inputs
    }


def test_short_history_is_explicitly_partial(harness: Harness) -> None:
    harness.transport.rows = harness.transport.rows[-5:]
    response = asyncio.run(harness.service.research("TEST"))
    assert response.status == "partial"
    assert response.flow.incomplete_history is True
    assert response.flow.trading_days == 5
    assert response.scores.flow.value is None
    assert "flow.window" in {item.key for item in response.missing_inputs}


def test_missing_shareholder_snapshots_are_empty_not_fabricated(harness: Harness) -> None:
    original = harness.transport._get_shareholder_composition

    def empty(year: int) -> dict[str, Any]:
        payload = original(year)
        payload["data"] = []
        return payload

    harness.transport._get_shareholder_composition = empty
    response = asyncio.run(harness.service.shareholders("TEST", 2026))
    assert response.status == "partial"
    assert response.as_of is None
    assert response.series == []
    assert response.categories == []
    assert response.missing_inputs[0].key == "shareholders"


def test_broker_gap_preserves_nulls(harness: Harness) -> None:
    original = harness.transport._get_broker_summary

    def with_gap(**params: Any) -> dict[str, Any]:
        payload = original(**params)
        if payload["data"]:
            payload["data"][0]["summary"] = [
                row for row in payload["data"][0]["summary"]
                if row["broker_code"] != "B0"
            ]
        return payload

    harness.transport._get_broker_summary = with_gap
    response = asyncio.run(harness.service.brokers("TEST", "1w", "B0"))
    assert response.status == "partial"
    assert response.series[0].points[0].net_idr is None
    assert all(point.cumulative_net_idr is None for point in response.series[0].points)
    assert "broker.B0" in {item.key for item in response.missing_inputs}


def test_service_rejects_bad_window_before_fetch(harness: Harness) -> None:
    with pytest.raises(InvalidWindowError):
        asyncio.run(harness.service.flow("TEST", "8d"))
    assert harness.transport.calls == {}
