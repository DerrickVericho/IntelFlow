"""Flow evidence for the requested trading window."""

from datetime import timedelta
from typing import Literal

from ..exceptions.research import InvalidWindowError
from ..models.common import MissingInput
from ..models.flow import FlowEvidence
from ..schemas.flow import FlowResponse
from ..sectors.mapper import (
    broker_evidence,
    foreign_broker_balance,
    foreign_evidence,
    liquidity_evidence,
)
from .base import ServiceBase
from .utils import normalize_symbol, research_status, source_record, unique_rows


class FlowService(ServiceBase):
    async def flow(
        self,
        symbol: str,
        window: Literal["1d", "5d", "20d"] = "20d",
    ) -> FlowResponse:
        symbol = normalize_symbol(symbol)
        if window not in ("1d", "5d", "20d"):
            raise InvalidWindowError("Window must be 1d, 5d, or 20d.")
        market_end = self._market_end()
        result, history = await self._history(symbol, end=market_end)
        count = int(window[:-1])
        selected = history[-count:]
        start, end = selected[0].date, selected[-1].date
        missing, sources = (
            [],
            [
                source_record(
                    "daily",
                    result,
                    today=self.today(),
                    as_of=end,
                    start=history[0].date,
                    end=end,
                )
            ],
        )
        if len(selected) < count:
            missing.append(
                MissingInput(
                    key="flow.window",
                    reason=f"Only {len(selected)} of {count} requested trading observations are available ({start} to {end}).",
                )
            )
        top = await self._optional(
            self.gateway.get_top_brokers(
                symbol,
                start=start.isoformat(),
                end=end.isoformat(),
                cohort="all",
                origin="all",
                foreign=False,
                n_brokers=10,
            ),
            "broker_top",
            missing,
        )
        broker_top_5d = None
        five_day_rows = selected[-5:]
        five_day_dates = {row.date for row in five_day_rows}
        five_day_start = five_day_rows[0].date
        if window == "20d":
            broker_top_5d = await self._optional(
                self.gateway.get_top_brokers(
                    symbol,
                    start=five_day_start.isoformat(),
                    end=end.isoformat(),
                    cohort="all",
                    origin="all",
                    foreign=False,
                    n_brokers=10,
                ),
                "broker_top_5d",
                missing,
            )
        foreign = await self._optional(
            self.gateway.get_foreign_flow(
                symbol,
                start=(market_end - timedelta(days=89)).isoformat(),
                end=market_end.isoformat(),
            ),
            "foreign_flow",
            missing,
        )
        foreign_top = None
        if window == "20d":
            foreign_top = await self._optional(
                self.gateway.get_top_brokers(
                    symbol,
                    start=start.isoformat(),
                    end=end.isoformat(),
                    cohort="all",
                    origin="all",
                    foreign=True,
                    n_brokers=10,
                ),
                "broker_foreign_top",
                missing,
            )
        selected_dates = {r.date for r in selected}
        activity_rows = []
        if window == "20d":
            cursor = start
            while cursor <= end:
                chunk_end = min(cursor + timedelta(days=13), end)
                activity = await self._optional(
                    self.gateway.get_broker_summary(
                        symbol, start=cursor.isoformat(), end=chunk_end.isoformat()
                    ),
                    "broker_activity",
                    missing,
                )
                if activity:
                    chunk = [r for r in activity.data.data if r.date in selected_dates]
                    activity_rows.extend(chunk)
                    sources.append(
                        source_record(
                            "broker_activity",
                            activity,
                            today=self.today(),
                            as_of=max((r.date for r in chunk), default=None),
                            start=cursor,
                            end=chunk_end,
                        )
                    )
                    if chunk_end < end - timedelta(days=7):
                        sources[-1].is_stale = False
                cursor = chunk_end + timedelta(days=1)
            activity_rows = unique_rows(activity_rows)
            activity_dates = {r.date for r in activity_rows}
            if activity_dates != selected_dates:
                missing.append(
                    MissingInput(
                        key="broker_activity",
                        reason=f"Daily broker activity covers {len(activity_dates)} of {len(selected_dates)} trading dates. Missing: "
                        + ", ".join(
                            str(d) for d in sorted(selected_dates - activity_dates)
                        )
                        + ".",
                    )
                )
        foreign_rows = (
            unique_rows([r for r in foreign.data.data if r.date in selected_dates])
            if foreign
            else []
        )
        if top:
            # Top rankings cannot be sliced locally: they must match the window.
            if top.data.start != start or top.data.end != end:
                missing.append(
                    MissingInput(
                        key="broker_top",
                        reason="Upstream ranking dates differ from requested window",
                    )
                )
                top = None
            else:
                sources.append(
                    source_record(
                        "broker_top",
                        top,
                        today=self.today(),
                        as_of=end,
                        start=start,
                        end=end,
                    )
                )
                if not top.data.top_buyers and not top.data.top_sellers:
                    missing.append(
                        MissingInput(
                            key="broker_top",
                            reason="No broker rankings available",
                        )
                    )
        if broker_top_5d:
            if (
                broker_top_5d.data.start != five_day_start
                or broker_top_5d.data.end != end
            ):
                missing.append(
                    MissingInput(
                        key="broker_top_5d",
                        reason="Five-day broker ranking dates differ from requested window",
                    )
                )
                broker_top_5d = None
            else:
                sources.append(
                    source_record(
                        "broker_top_5d",
                        broker_top_5d,
                        today=self.today(),
                        as_of=end,
                        start=five_day_start,
                        end=end,
                    )
                )
                if (
                    not broker_top_5d.data.top_buyers
                    and not broker_top_5d.data.top_sellers
                ):
                    missing.append(
                        MissingInput(
                            key="broker_top_5d",
                            reason="No five-day broker rankings available",
                        )
                    )
        if foreign_top:
            if (
                foreign_top.data.start != start
                or foreign_top.data.end != end
                or not foreign_top.data.foreign
            ):
                missing.append(
                    MissingInput(
                        key="broker_foreign_top",
                        reason="Foreign ranking dates or investor filter differ from requested window",
                    )
                )
                foreign_top = None
            else:
                sources.append(
                    source_record(
                        "broker_foreign_top",
                        foreign_top,
                        today=self.today(),
                        as_of=end,
                        start=start,
                        end=end,
                    )
                )
                if foreign_broker_balance(foreign_top.data) is None:
                    missing.append(
                        MissingInput(
                            key="broker_foreign_top",
                            reason="No foreign-ranked net broker balance available",
                        )
                    )
        if foreign:
            sources.append(
                source_record(
                    "foreign_flow",
                    foreign,
                    today=self.today(),
                    as_of=foreign_rows[-1].date if foreign_rows else None,
                    start=start,
                    end=end,
                )
            )
            if {r.date for r in foreign_rows} != selected_dates:
                missing.append(
                    MissingInput(
                        key="foreign_flow",
                        reason=f"Foreign flow covers {len(foreign_rows)} of {len(selected)} trading dates. Missing: "
                        + ", ".join(
                            str(d)
                            for d in sorted(
                                selected_dates - {r.date for r in foreign_rows}
                            )
                        )
                        + ".",
                    )
                )
        evidence = FlowEvidence(
            window=window,
            effective_start=start,
            effective_end=end,
            trading_days=len(selected),
            incomplete_history=len(selected) < count,
            broker_summary=broker_evidence(top.data if top else None, activity_rows),
            broker_summary_5d=(
                broker_evidence(
                    broker_top_5d.data,
                    [row for row in activity_rows if row.date in five_day_dates],
                )
                if broker_top_5d
                else None
            ),
            foreign_broker_balance=foreign_broker_balance(
                foreign_top.data if foreign_top else None
            ),
            foreign_flow=foreign_evidence(foreign_rows),
            liquidity=liquidity_evidence(history, selected_dates),
        )
        invalid_liquidity_dates = [
            p.date
            for p in evidence.liquidity.series
            if p.close_idr <= 0 or p.volume_shares < 0
        ]
        if invalid_liquidity_dates:
            missing.append(
                MissingInput(
                    key="liquidity.value",
                    reason="Closing price or share volume is invalid on: "
                    + ", ".join(str(d) for d in invalid_liquidity_dates)
                    + ".",
                )
            )
        if any(p.volume_ratio is None for p in evidence.liquidity.series):
            missing.append(
                MissingInput(
                    key="liquidity.baseline",
                    reason="Volume needs 20 earlier observations with a positive average. Incomplete baseline on: "
                    + ", ".join(
                        str(p.date)
                        for p in evidence.liquidity.series
                        if p.volume_ratio is None
                    )
                    + ".",
                )
            )
        return FlowResponse(
            symbol=symbol,
            as_of=end,
            status=research_status(missing, sources),
            missing_inputs=missing,
            sources=sources,
            flow=evidence,
        )
