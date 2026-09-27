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
        "daily",
        "broker_top",
        "foreign_flow",
        "company_financials",
        "company_valuation",
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


def test_missing_shareholder_snapshots_are_empty_not_fabricated(
    harness: Harness,
) -> None:
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
                row
                for row in payload["data"][0]["summary"]
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


def test_available_components_do_not_hide_missing_foreign_date(
    harness: Harness,
) -> None:
    original = harness.transport._get_foreign_flow
    missing_date = harness.transport.days[-3].isoformat()

    def with_gap(**params: Any) -> dict[str, Any]:
        payload = original(**params)
        payload["data"] = [
            row for row in payload["data"] if row["date"] != missing_date
        ]
        return payload

    harness.transport._get_foreign_flow = with_gap
    response = asyncio.run(harness.service.research("TEST"))
    assert all(
        component.value is not None for component in response.scores.flow.components
    )
    assert response.scores.flow.value is None
    assert response.scores.combined.value is None
    assert "19 of 20" in response.scores.flow.reason
    assert missing_date in response.scores.flow.reason
    assert response.scores.combined.components[0].reason == response.scores.flow.reason


def test_partial_volume_baseline_explains_null_aggregate(harness: Harness) -> None:
    harness.transport.rows = harness.transport.rows[-35:]
    response = asyncio.run(harness.service.research("TEST"))
    assert all(
        component.value is not None for component in response.scores.flow.components
    )
    assert response.scores.flow.value is None
    assert "Incomplete baseline on:" in response.scores.flow.reason
    assert str(response.flow.effective_start) in response.scores.flow.reason


def test_complete_coverage_has_scores_and_dated_price_change(harness: Harness) -> None:
    response = asyncio.run(harness.service.research("TEST"))
    latest, previous = harness.transport.rows[-1], harness.transport.rows[-2]
    assert response.scores.flow.value is not None
    assert response.scores.combined.value is not None
    assert response.scores.flow.reason is None
    assert str(response.company.close_date) == latest["date"]
    assert str(response.company.previous_close_date) == previous["date"]
    assert response.company.previous_close_idr == previous["close"]
    assert response.company.change_idr == latest["close"] - previous["close"]
    assert response.company.change_percent == round(100 / previous["close"], 4)
    assert harness.transport.calls["get_daily"] == 1
    broker_point = next(
        p for p in response.key_points if p.title == "Broker concentration"
    )
    assert len(broker_point.items) == 3
    assert broker_point.category == "flow"
    assert ";" not in broker_point.text
    assert any(p.category == "fundamental" for p in response.key_points)


@pytest.mark.parametrize("close_change", [-25, 0, 25])
def test_price_change_preserves_direction(harness: Harness, close_change: int) -> None:
    previous = harness.transport.rows[-2]["close"]
    harness.transport.rows[-1]["close"] = previous + close_change
    response = asyncio.run(harness.service.research("TEST"))
    assert response.company.change_idr == close_change
    assert response.company.change_percent == round(100 * close_change / previous, 4)


def test_one_observation_cannot_manufacture_price_change(harness: Harness) -> None:
    harness.transport.rows = harness.transport.rows[-1:]
    response = asyncio.run(harness.service.research("TEST"))
    assert response.company.last_close_idr is not None
    assert response.company.previous_close_date is None
    assert response.company.change_idr is None
    assert response.company.change_percent is None
