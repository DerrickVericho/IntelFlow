"""Boundary cases for the user-defined IDR flow thresholds."""

from datetime import date, timedelta

import pytest

from src.backend.models.flow import (
    Breadth,
    BrokerDailyPoint,
    BrokerSummary,
    FlowEvidence,
    ForeignFlow,
    ForeignPoint,
    Liquidity,
    LiquidityPoint,
)
from src.backend.scoring.components import (
    broker_flow_value,
    foreign_flow_value,
    liquidity_value,
)


def liquidity_point(day: date, volume: int) -> LiquidityPoint:
    return LiquidityPoint(
        date=day,
        close_idr=1_000,
        volume_shares=volume,
        average_volume_shares=None,
        volume_ratio=None,
        baseline_observations=0,
    )


def test_liquidity_uses_idr_five_billion_per_day_and_zero_volume() -> None:
    start = date(2026, 9, 1)
    flow = FlowEvidence(
        window="20d",
        liquidity=Liquidity(
            series=[
                liquidity_point(start, 5_000_000),
                liquidity_point(start + timedelta(days=1), 0),
            ]
        ),
    )
    assert liquidity_value(flow) == 50


def foreign_case(ratio: float, share_percent: float) -> FlowEvidence:
    day = date(2026, 9, 1)
    return FlowEvidence(
        window="20d",
        foreign_broker_balance=Breadth(
            top_n=5,
            buyer_net_idr=125,
            seller_net_idr=-75,
            balance_idr=50,
            balance_ratio=ratio,
            buyer_count=5,
            seller_count=5,
        ),
        foreign_flow=ForeignFlow(
            series=[
                ForeignPoint(
                    date=day,
                    buy_idr=100,
                    sell_idr=50,
                    net_inflow_idr=50,
                    cumulative_net_inflow_idr=50,
                    foreign_share_percent=share_percent,
                )
            ]
        ),
    )


@pytest.mark.parametrize(
    "ratio,share,expected",
    [
        (0.25, 40, 100),
        (-0.25, 40, 0),
        (0, 40, 50),
        (0.25, 20, 75),
        (-0.25, 20, 25),
        (1, 0, 50),
    ],
)
def test_foreign_direction_and_participation(
    ratio: float, share: float, expected: float
) -> None:
    assert foreign_flow_value(foreign_case(ratio, share)) == expected


def test_foreign_missing_ranked_balance_is_unavailable() -> None:
    flow = foreign_case(0.25, 40)
    flow.foreign_broker_balance = None
    assert foreign_flow_value(flow) is None


def broker_summary(ratio: float, daily_net: int, days: int) -> BrokerSummary:
    start = date(2026, 9, 1)
    breadth = [
        Breadth(
            top_n=n,
            buyer_net_idr=125,
            seller_net_idr=-75,
            balance_idr=50,
            balance_ratio=ratio,
            buyer_count=n,
            seller_count=n,
        )
        for n in (3, 5)
    ]
    daily = [
        BrokerDailyPoint(
            date=start + timedelta(days=i),
            total_buy_idr=1_000,
            top3_net_idr=100,
            top5_net_idr=100,
            top3_seller_net_idr=daily_net - 100,
            top5_seller_net_idr=daily_net - 100,
        )
        for i in range(days)
    ]
    return BrokerSummary(breadth=breadth, daily=daily)


def broker_case(
    ratio: float,
    daily_net: int,
    *,
    short_ratio: float | None = None,
    short_daily_net: int | None = None,
) -> FlowEvidence:
    return FlowEvidence(
        window="20d",
        broker_summary=broker_summary(ratio, daily_net, 20),
        broker_summary_5d=broker_summary(
            ratio if short_ratio is None else short_ratio,
            daily_net if short_daily_net is None else short_daily_net,
            5,
        ),
    )


def test_broker_full_accumulation_and_distribution_reach_endpoints() -> None:
    assert broker_flow_value(broker_case(0.25, 100)) == 100
    assert broker_flow_value(broker_case(-0.25, -100)) == 0


def test_broker_daily_consistency_includes_seller_side() -> None:
    flow = broker_case(0.25, 100)
    flow.broker_summary.daily[0].top3_seller_net_idr = -200
    flow.broker_summary.daily[0].top5_seller_net_idr = -200
    assert broker_flow_value(flow) < 100


def test_broker_flat_evidence_is_neutral() -> None:
    assert broker_flow_value(broker_case(0, 0)) == 50


def test_broker_score_weights_independent_five_day_window_more_heavily() -> None:
    recent_accumulation = broker_case(
        -0.20, -100, short_ratio=0.20, short_daily_net=100
    )
    recent_distribution = broker_case(
        0.20, 100, short_ratio=-0.20, short_daily_net=-100
    )
    assert broker_flow_value(recent_accumulation) == 65
    assert broker_flow_value(recent_distribution) == 35


def test_broker_direction_saturates_at_point_two() -> None:
    assert broker_flow_value(broker_case(0.20, 100)) == 100
    assert broker_flow_value(broker_case(-0.20, -100)) == 0


def test_broker_needs_at_least_four_recent_observations() -> None:
    flow = broker_case(0.20, 100)
    flow.broker_summary_5d.daily = flow.broker_summary_5d.daily[:3]
    assert broker_flow_value(flow) is None
