"""Application use cases: cached inputs -> evidence -> scores -> public models."""

import logging
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta
from typing import Literal, TypeVar
from zoneinfo import ZoneInfo

from ..exceptions.research import (
    DataNotFoundError,
    InvalidBrokersError,
    InvalidWindowError,
    InvalidYearError,
    ResearchUnavailableError,
)
from ..exceptions.sectors import SectorsError
from ..models.common import MissingInput
from ..models.flow import FlowEvidence
from ..models.research import Company, KeyPoint
from ..schemas.brokers import BrokerPoint, BrokerResponse, BrokerSeries
from ..schemas.flow import FlowResponse
from ..schemas.prices import PricePoint, PriceResponse
from ..schemas.research import ResearchResponse
from ..schemas.shareholders import Category, ShareholderPoint, ShareholderResponse
from ..scoring.research import calculate
from ..sectors.utils import latest_provider_date
from ..sectors.gateway import SectorsGateway
from ..sectors.mapper import (
    broker_evidence,
    fundamentals_evidence,
    foreign_evidence,
    liquidity_evidence,
)
from ..sectors.schemas.transactions import DailyTransaction
from ..sectors.types import Retrieved
from .utils import (
    market_range,
    normalize_symbol,
    research_status,
    source_record,
    unique_rows,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")


class ResearchService:
    def __init__(
        self,
        gateway: SectorsGateway,
        today: Callable[[], date] | None = None,
        utc_today: Callable[[], date] | None = None,
    ) -> None:
        self.gateway = gateway
        self.today = today or (lambda: datetime.now(ZoneInfo("Asia/Jakarta")).date())
        self.utc_today = utc_today or (lambda: datetime.now(UTC).date())

    def _market_end(self) -> date:
        return latest_provider_date(self.today(), self.utc_today())

    async def _optional(
        self,
        call: Awaitable[Retrieved[T]],
        key: str,
        missing: list[MissingInput],
    ) -> Retrieved[T] | None:
        try:
            return await call
        except SectorsError as exc:
            logger.warning(
                "Research input unavailable",
                extra={
                    "operation": key,
                    "error_type": type(exc).__name__,
                    "upstream_status": exc.status_code,
                },
            )
            missing.append(MissingInput(key=key, reason=type(exc).__name__))
            return None

    async def _history(
        self,
        symbol: str,
        *,
        end: date | None = None,
    ) -> tuple[Retrieved[list[DailyTransaction]], list[DailyTransaction]]:
        end = end or self._market_end()
        result = await self.gateway.get_daily(
            symbol, start=(end - timedelta(days=89)).isoformat(), end=end.isoformat()
        )
        rows = unique_rows(
            [r for r in result.data if end - timedelta(days=89) <= r.date <= end]
        )
        if not rows:
            raise DataNotFoundError(
                "No price observations available for this symbol in the supported history."
            )
        return result, rows

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
                    key="flow.window", reason="Insufficient trading observations"
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
        foreign = await self._optional(
            self.gateway.get_foreign_flow(
                symbol,
                start=(market_end - timedelta(days=89)).isoformat(),
                end=market_end.isoformat(),
            ),
            "foreign_flow",
            missing,
        )
        selected_dates = {r.date for r in selected}
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
                            key="broker_top", reason="No broker rankings available"
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
                        reason="Foreign series does not cover every selected observation",
                    )
                )
        evidence = FlowEvidence(
            window=window,
            effective_start=start,
            effective_end=end,
            trading_days=len(selected),
            incomplete_history=len(selected) < count,
            broker_summary=broker_evidence(top.data if top else None),
            foreign_flow=foreign_evidence(foreign_rows),
            liquidity=liquidity_evidence(history, selected_dates),
        )
        if any(p.volume_ratio is None for p in evidence.liquidity.series):
            missing.append(
                MissingInput(
                    key="liquidity.baseline",
                    reason="Some dates lack 20 prior observations or have a zero baseline",
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

    async def research(self, symbol: str) -> ResearchResponse:
        response = await self.flow(symbol, "20d")
        symbol = response.symbol
        missing, sources = list(response.missing_inputs), list(response.sources)
        sections = {}
        for name in ("overview", "financials", "valuation"):
            key = "company_" + name
            result = await self._optional(
                self.gateway.get_company_report(symbol, sections=[name]), key, missing
            )
            section = getattr(result.data, name, None) if result else None
            if result and section is None:
                missing.append(
                    MissingInput(key=key, reason="Requested report section is absent")
                )
            sections[name] = (result, section)
            if result and section is not None:
                period, as_of = None, None
                if name == "financials":
                    years = [r.year for r in section.historical_financials]
                    period = str(max(years)) if years else None
                if name == "valuation":
                    as_of = section.latest_close_date
                    period = (
                        str(
                            max(
                                (r.year for r in section.historical_valuation),
                                default="",
                            )
                        )
                        or None
                    )
                source = source_record(
                    key,
                    result,
                    today=self.today(),
                    as_of=as_of,
                    period=period,
                )
                if name == "financials" and period:
                    source.is_stale = int(period) < self.today().year - 2
                sources.append(source)
        overview = sections["overview"][1]
        financials, valuation = sections["financials"][1], sections["valuation"][1]
        fundamentals = fundamentals_evidence(financials, valuation)
        scores = calculate(response.flow, fundamentals, financials=financials)
        # Partial observation windows must not produce a full-window flow score.
        if any(
            m.key in {"flow.window", "foreign_flow", "broker_top", "liquidity.baseline"}
            for m in missing
        ):
            scores.flow.value = None
            scores.flow.reason = "Incomplete flow input coverage"
            scores.combined.value = None
            scores.combined.reason = "Flow score unavailable"
            scores.combined.components[0].value = None
            scores.combined.components[0].reason = "Incomplete flow input coverage"
            scores.research_state = "Insufficient evidence"
        for name in ("flow", "fundamental", "combined"):
            score = getattr(scores, name)
            if score.value is None:
                missing.append(
                    MissingInput(
                        key="scores." + name,
                        reason=score.reason or "Insufficient evidence",
                    )
                )
            for component in score.components:
                if component.value is None:
                    missing.append(
                        MissingInput(
                            key=f"scores.{name}.{component.key}",
                            reason=component.reason or "Insufficient evidence",
                        )
                    )
        for group in fundamentals.groups:
            for m in group.metrics:
                if m.availability == "unavailable":
                    missing.append(
                        MissingInput(
                            key="fundamentals." + m.key,
                            reason=m.reason or "Unavailable",
                        )
                    )
        identity = next((r.data.company_name for r, _ in sections.values() if r), None)
        company = Company(
            name=identity,
            sector=overview.sector if overview else None,
            sub_sector=overview.sub_sector if overview else None,
            last_close_idr=response.flow.liquidity.series[-1].close_idr,
        )
        points = []
        breadth = response.flow.broker_summary.breadth
        if breadth:
            directions = {
                b.balance_ratio > 0 for b in breadth if b.balance_ratio is not None
            }
            points.append(
                KeyPoint(
                    kind="conflict" if len(directions) > 1 else "evidence",
                    title="Broker concentration",
                    text="Top buyer/seller balance: "
                    + "; ".join(
                        f"top {b.top_n}: IDR {b.balance_idr:,}" for b in breadth
                    ),
                    source_keys=["broker_top"],
                )
            )
        foreign = response.flow.foreign_flow
        if foreign.net_inflow_idr is not None:
            points.append(
                KeyPoint(
                    kind="evidence",
                    title="Foreign investor flow",
                    text=(
                        f"Net IDR {foreign.net_inflow_idr:,} across "
                        f"{len(foreign.series)} observations; "
                        f"{foreign.positive_days} positive-flow days."
                    ),
                    source_keys=["foreign_flow"],
                )
            )
        ratio = response.flow.liquidity.latest_vs_average_ratio
        if ratio is not None:
            points.append(
                KeyPoint(
                    kind="evidence",
                    title="Trading activity",
                    text=f"Latest volume is {ratio:.2f} times its preceding 20-observation mean.",
                    source_keys=["daily"],
                )
            )
        points.append(
            KeyPoint(
                kind=(
                    "evidence"
                    if scores.fundamental.value is not None
                    else "unavailable"
                ),
                title="Fundamental support",
                text=(
                    f"{scores.research_state}. Financial reporting year: "
                    f"{fundamentals.reporting_period or 'unavailable'}."
                ),
                source_keys=[s.key for s in sources if s.key.startswith("company_")],
            )
        )
        if missing:
            points.append(
                KeyPoint(
                    kind="unavailable",
                    title="Incomplete evidence",
                    text=(
                        f"{len(missing)} input or calculation limitations; "
                        "inspect missing_inputs."
                    ),
                    source_keys=[],
                )
            )
        return ResearchResponse(
            symbol=symbol,
            as_of=response.as_of,
            status=research_status(missing, sources),
            sources=sources,
            missing_inputs=missing,
            flow=response.flow,
            company=company,
            scores=scores,
            key_points=points,
            fundamentals=fundamentals,
        )

    async def prices(self, symbol: str, range_: str) -> PriceResponse:
        symbol = normalize_symbol(symbol)
        start, end = market_range(range_, self._market_end())
        result, history = await self._history(symbol, end=end)
        rows = [r for r in history if start <= r.date <= end]
        source = source_record(
            "daily",
            result,
            today=self.today(),
            as_of=rows[-1].date if rows else None,
            start=start,
            end=end,
        )
        incomplete = (
            not rows
            or (rows[0].date - start).days > 7
            or (end - rows[-1].date).days > 7
        )
        missing = (
            [
                MissingInput(
                    key="prices", reason="Requested interval has incomplete history"
                )
            ]
            if incomplete
            else []
        )
        return PriceResponse(
            symbol=symbol,
            as_of=source.as_of,
            status=research_status(missing, [source]),
            sources=[source],
            missing_inputs=missing,
            range=range_,
            effective_start=rows[0].date if rows else None,
            effective_end=source.as_of,
            incomplete_history=incomplete,
            series=[PricePoint(**r.model_dump(exclude={"symbol"})) for r in rows],
        )

    async def shareholders(
        self,
        symbol: str,
        year: int | None = None,
    ) -> ShareholderResponse:
        symbol = normalize_symbol(symbol)
        year = year if year is not None else self.today().year
        if not 2021 <= year <= self.today().year:
            raise InvalidYearError("Year must be between 2021 and the current year.")
        result = await self.gateway.get_shareholder_composition(symbol, year=year)
        rows = unique_rows([r for r in result.data.data if r.date.year == year])
        categories = (
            [
                k
                for k in type(rows[0]).model_fields
                if k.endswith(("_l", "_f")) and not k.startswith("total_")
            ]
            if rows
            else []
        )
        points = [
            ShareholderPoint(
                date=r.date,
                shares_number=r.shares_number,
                holdings={k: getattr(r, k) for k in categories},
                total_local=r.total_l,
                total_foreign=r.total_f,
                shareholder_count=r.numbers_of_shareholders,
                shareholder_count_change=r.change_in_shareholders,
            )
            for r in rows
        ]
        source = source_record(
            "shareholders",
            result,
            today=self.today(),
            as_of=rows[-1].date if rows else None,
            max_age=75,
        )
        if year < self.today().year:
            source.is_stale = False
        missing = (
            []
            if rows
            else [MissingInput(key="shareholders", reason="No snapshots in this year")]
        )
        return ShareholderResponse(
            symbol=symbol,
            as_of=source.as_of,
            status=research_status(missing, [source]),
            sources=[source],
            missing_inputs=missing,
            year=year,
            supported_years=list(range(2021, self.today().year + 1)),
            categories=[
                Category(
                    key=k,
                    label=k[:-2].replace("_", " ").title()
                    + (" Local" if k.endswith("_l") else " Foreign"),
                )
                for k in categories
            ],
            series=points,
        )

    async def brokers(
        self,
        symbol: str,
        range_: str,
        brokers: str | None = None,
    ) -> BrokerResponse:
        symbol = normalize_symbol(symbol)
        start, end = market_range(range_, self._market_end())
        selected = None
        if brokers is not None:
            selected = list(
                dict.fromkeys(c.strip().upper() for c in brokers.split(","))
            )
            if len(selected) > 10 or any(
                not re.fullmatch(r"[A-Z0-9]{2}", c) for c in selected
            ):
                raise InvalidBrokersError("Select 1–10 two-character broker codes.")
        missing, sources, rows = [], [], []
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + timedelta(days=13), end)
            key = "brokers_" + cursor.isoformat()
            result = await self._optional(
                self.gateway.get_broker_summary(
                    symbol, start=cursor.isoformat(), end=chunk_end.isoformat()
                ),
                key,
                missing,
            )
            if result:
                chunk = [r for r in result.data.data if cursor <= r.date <= chunk_end]
                rows.extend(chunk)
                sources.append(
                    source_record(
                        key,
                        result,
                        today=self.today(),
                        as_of=max((r.date for r in chunk), default=None),
                        start=cursor,
                        end=chunk_end,
                    )
                )
                # Closed historical chunks are expected to have old observations.
                if chunk_end < end - timedelta(days=7):
                    sources[-1].is_stale = False
            cursor = chunk_end + timedelta(days=1)
        if not sources:
            raise ResearchUnavailableError("No broker history could be retrieved.")
        rows = unique_rows(rows)
        available = sorted({b.broker_code for r in rows for b in r.summary})
        totals = {
            c: sum(b.nval for r in rows for b in r.summary if b.broker_code == c)
            for c in available
        }
        buyers = sorted(
            (c for c in available if totals[c] > 0), key=lambda c: (-totals[c], c)
        )[:3]
        sellers = sorted(
            (c for c in available if totals[c] < 0), key=lambda c: (totals[c], c)
        )[:3]
        defaults = list(dict.fromkeys(buyers + sellers))
        selected = defaults if selected is None else selected
        series = []
        has_chunk_gap = bool(missing)
        for code in selected:
            total, points, has_gap = 0, [], has_chunk_gap
            for row in rows:
                b = next((b for b in row.summary if b.broker_code == code), None)
                # An absent row is not proof of zero activity; retain a gap.
                if b:
                    total += b.nval
                else:
                    has_gap = True
                points.append(
                    BrokerPoint(
                        date=row.date,
                        buy_idr=b.bval if b else None,
                        sell_idr=b.sval if b else None,
                        net_idr=b.nval if b else None,
                        cumulative_net_idr=total if b and not has_gap else None,
                    )
                )
            if code not in available:
                missing.append(
                    MissingInput(
                        key="broker." + code,
                        reason="Broker has no observations in the requested interval",
                    )
                )
            elif has_gap:
                missing.append(
                    MissingInput(
                        key="broker." + code,
                        reason=(
                            "Daily gaps; cumulative series cannot be calculated "
                            "across missing observations"
                        ),
                    )
                )
            series.append(BrokerSeries(broker_code=code, points=points))
        if not rows:
            missing.append(
                MissingInput(
                    key="brokers", reason="No observations in requested interval"
                )
            )
        if rows and ((rows[0].date - start).days > 7 or (end - rows[-1].date).days > 7):
            missing.append(
                MissingInput(
                    key="brokers.coverage",
                    reason="Observed dates do not cover the requested interval",
                )
            )
        return BrokerResponse(
            symbol=symbol,
            as_of=rows[-1].date if rows else None,
            status=research_status(missing, sources),
            sources=sources,
            missing_inputs=missing,
            range=range_,
            effective_start=start,
            effective_end=end,
            incomplete_history=bool(missing),
            default_brokers=defaults,
            selected_brokers=selected,
            available_brokers=available,
            series=series,
        )
