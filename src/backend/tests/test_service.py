"""Research use cases and failure policy, without asserting score formulas."""

import asyncio
from datetime import date
from typing import Any

import pytest

from src.backend.exceptions.research import InvalidWindowError
from src.backend.exceptions.sectors import SectorsNotFoundError, SectorsUpstreamError
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


@pytest.mark.parametrize("year", [2024, 2025])
def test_historical_shareholder_year_reaches_provider(harness: Harness, year: int) -> None:
    response = asyncio.run(harness.service.shareholders("TEST", year))
    assert response.year == year
    assert response.series[0].date.year == year
    assert harness.transport.calls["get_shareholder_composition"] == 1


def test_historical_null_counts_keep_composition_rows(harness: Harness) -> None:
    original = harness.transport._get_shareholder_composition

    def with_missing_counts(year: int) -> dict[str, Any]:
        payload = original(year)
        payload["data"][0]["numbers_of_shareholders"] = None
        payload["data"][0]["change_in_shareholders"] = None
        return payload

    harness.transport._get_shareholder_composition = with_missing_counts
    response = asyncio.run(harness.service.shareholders("TEST", 2025))
    assert response.status == "partial"
    assert response.series[0].holdings["corporate_l"] == 100
    assert response.series[0].shareholder_count is None
    assert response.series[0].shareholder_count_change is None
    assert "shareholders.count" in {item.key for item in response.missing_inputs}


def test_missing_historical_shareholder_dataset_is_empty_not_error(
    harness: Harness,
) -> None:
    harness.transport.failures["get_shareholder_composition"] = SectorsNotFoundError(
        "private provider detail"
    )
    response = asyncio.run(harness.service.shareholders("TEST", 2025))
    assert response.status == "partial"
    assert response.year == 2025
    assert response.series == []
    assert response.sources == []
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


def test_one_missing_foreign_date_keeps_scored_result_with_coverage_warning(
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
    assert response.scores.flow.value is not None
    assert response.scores.combined.value is not None
    assert response.scores.calculation_version == "draft-v0.7"
    assert "19 of 20" in response.scores.flow.reason
    assert missing_date in response.scores.flow.reason
    assert response.scores.combined.components[0].reason == response.scores.flow.reason
    assert "partial coverage" in response.scores.combined.reason.lower()


def test_partial_volume_baseline_does_not_block_idr_liquidity_score(harness: Harness) -> None:
    harness.transport.rows = harness.transport.rows[-35:]
    response = asyncio.run(harness.service.research("TEST"))
    assert all(
        component.value is not None for component in response.scores.flow.components
    )
    assert response.scores.flow.value is not None
    assert response.scores.flow.reason is None
    assert "liquidity.baseline" in {item.key for item in response.missing_inputs}


def test_sixteen_volume_baselines_keep_scored_result(harness: Harness) -> None:
    harness.transport.rows = harness.transport.rows[-36:]
    response = asyncio.run(harness.service.research("TEST"))
    assert response.flow.trading_days == 20
    assert sum(point.volume_ratio is not None for point in response.flow.liquidity.series) == 16
    assert response.scores.flow.value is not None
    assert response.scores.combined.value is not None
    assert response.status == "partial"
    assert response.scores.flow.reason is None


def test_fifteen_foreign_dates_are_below_scoring_minimum(harness: Harness) -> None:
    original = harness.transport._get_foreign_flow
    missing_dates = {day.isoformat() for day in harness.transport.days[-5:]}

    def with_gap(**params: Any) -> dict[str, Any]:
        payload = original(**params)
        payload["data"] = [
            row for row in payload["data"] if row["date"] not in missing_dates
        ]
        return payload

    harness.transport._get_foreign_flow = with_gap
    response = asyncio.run(harness.service.research("TEST"))
    assert all(component.value is not None for component in response.scores.flow.components)
    assert response.scores.flow.value is None
    assert response.scores.combined.value is None
    assert "15 of 20" in response.scores.flow.reason


def test_one_missing_broker_day_keeps_score_with_coverage_warning(harness: Harness) -> None:
    original = harness.transport._get_broker_summary
    missing_date = harness.transport.days[-3].isoformat()

    def with_gap(**params: Any) -> dict[str, Any]:
        payload = original(**params)
        payload["data"] = [row for row in payload["data"] if row["date"] != missing_date]
        return payload

    harness.transport._get_broker_summary = with_gap
    response = asyncio.run(harness.service.research("TEST"))
    assert len(response.flow.broker_summary.daily) == 19
    assert response.scores.flow.value is not None
    assert response.scores.combined.value is not None
    assert "Daily broker activity covers 19 of 20" in response.scores.flow.reason
    assert missing_date in response.scores.flow.reason


def test_three_recent_broker_days_are_below_scoring_minimum(harness: Harness) -> None:
    original = harness.transport._get_broker_summary
    missing_dates = {day.isoformat() for day in harness.transport.days[-2:]}

    def with_recent_gap(**params: Any) -> dict[str, Any]:
        payload = original(**params)
        payload["data"] = [
            row for row in payload["data"] if row["date"] not in missing_dates
        ]
        return payload

    harness.transport._get_broker_summary = with_recent_gap
    response = asyncio.run(harness.service.research("TEST"))
    assert len(response.flow.broker_summary.daily) == 18
    assert len(response.flow.broker_summary_5d.daily) == 3
    assert response.scores.flow.value is None
    assert response.scores.combined.value is None
    assert "Daily broker activity covers 18 of 20" in response.scores.flow.reason


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
    assert harness.transport.calls["get_top_brokers"] == 3
    assert response.flow.broker_summary_5d is not None
    assert len(response.flow.broker_summary_5d.daily) == 5
    assert response.flow.foreign_broker_balance is not None
    assert response.flow.foreign_broker_balance.balance_ratio > 0
    broker_point = next(
        p for p in response.key_points if p.title == "Broker balance by window"
    )
    assert len(broker_point.items) == 4
    assert broker_point.source_keys == ["broker_top_5d", "broker_top"]
    assert broker_point.category == "flow"
    assert ";" not in broker_point.text
    assert any(p.category == "fundamental" for p in response.key_points)


def test_foreign_scoring_uses_foreign_net_not_overall_net(harness: Harness) -> None:
    original = harness.transport._get_top_brokers

    def divergent_ranking(**params: Any) -> dict[str, Any]:
        payload = original(**params)
        if params.get("foreign"):
            for row in payload["top_buyers"]:
                row["net_idr"] = -1_000_000
                row["foreign_net_idr"] = 125
            for row in payload["top_sellers"]:
                row["net_idr"] = 1_000_000
                row["foreign_net_idr"] = -75
        return payload

    harness.transport._get_top_brokers = divergent_ranking
    response = asyncio.run(harness.service.research("TEST"))
    assert response.flow.foreign_broker_balance.balance_ratio == 0.25
    foreign_component = next(c for c in response.scores.flow.components if c.key == "foreign_flow")
    assert foreign_component.value == 87.5  # Fixture participation: 30% / 40%.


def test_missing_foreign_ranking_does_not_fabricate_flow_score(harness: Harness) -> None:
    original = harness.transport._get_top_brokers

    def without_foreign_ranking(**params: Any) -> dict[str, Any]:
        payload = original(**params)
        if params.get("foreign"):
            payload["top_buyers"] = []
            payload["top_sellers"] = []
        return payload

    harness.transport._get_top_brokers = without_foreign_ranking
    response = asyncio.run(harness.service.research("TEST"))
    assert response.flow.foreign_broker_balance is None
    assert response.scores.flow.value is None
    assert response.scores.combined.value is None
    assert "broker_foreign_top" in {item.key for item in response.missing_inputs}


def test_fundamental_scores_average_available_recent_observations(harness: Harness) -> None:
    original = harness.transport._get_company_report

    def with_sparse_fundamentals(sections: list[str]) -> dict[str, Any]:
        payload = original(sections)
        if "financials" in payload:
            by_year = {row["year"]: row for row in payload["financials"]["historical_financials"]}
            by_year[2023].update(earnings=-1000, operating_cash_flow=100, free_cash_flow=-100)
            by_year[2024].update(earnings=-1000, operating_cash_flow=100, free_cash_flow=None)
            by_year[2025].update(earnings=-1000, operating_cash_flow=-100, free_cash_flow=-100)
        if "valuation" in payload:
            by_year = {row["year"]: row for row in payload["valuation"]["historical_valuation"]}
            for year in (2024, 2025, 2026):
                by_year[year].update(pe=None, pb=None, pcf=None)
            for year, value in ((2022, 1), (2023, 1.2), (2024, 2), (2025, None), (2026, 10)):
                by_year[year]["ps"] = value
        return payload

    harness.transport._get_company_report = with_sparse_fundamentals
    response = asyncio.run(harness.service.research("TEST"))
    components = {component.key: component.value for component in response.scores.fundamental.components}
    assert components["cash_flow"] == 40  # Two positive observations / five available.
    assert components["valuation"] == 23.09  # Two comparable PS observations / two.
    assert response.scores.fundamental.value is not None
    assert response.scores.combined.value is not None


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
