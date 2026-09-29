"""Aggregate dated evidence and deterministic IntelScore results."""

from ..models.common import MissingInput
from ..models.research import Company, KeyPoint
from ..schemas.research import ResearchResponse
from ..scoring.research import calculate
from ..sectors.mapper import fundamentals_evidence
from .flow import FlowService
from .utils import research_status, source_record


class IntelScoreService(FlowService):
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
        # Keep a dated partial-coverage score when the scoring minimum is met.
        coverage_issues = [
            m
            for m in missing
            if m.key
            in {
                "flow.window",
                "foreign_flow",
                "broker_top",
                "broker_top_5d",
                "broker_foreign_top",
                "broker_activity",
                "liquidity.value",
            }
        ]
        if coverage_issues:
            coverage_labels = {
                "flow.window": "Trading history",
                "foreign_flow": "Foreign investor flow",
                "broker_top": "Broker rankings",
                "broker_top_5d": "Five-day broker rankings",
                "broker_foreign_top": "Foreign investor broker rankings",
                "broker_activity": "Daily broker activity",
                "liquidity.value": "Daily liquidity value",
            }
            coverage_reason = "Flow coverage is incomplete. " + " ".join(
                f"{coverage_labels[m.key]}: {m.reason}" for m in coverage_issues
            )
            if scores.flow.value is None or any(
                m.key
                in {"flow.window", "broker_top", "broker_top_5d", "broker_foreign_top"}
                for m in coverage_issues
            ):
                scores.flow.value = None
                scores.flow.reason = (
                    "Insufficient coverage for a Flow Score. " + coverage_reason
                )
                scores.combined.value = None
                scores.combined.reason = "Flow score unavailable"
                scores.combined.components[0].value = None
                scores.research_state = "Insufficient evidence"
            else:
                scores.flow.reason = (
                    "Partial coverage: score uses available observations. "
                    + coverage_reason
                )
                scores.combined.reason = (
                    "Includes a Flow Score with partial coverage. "
                    "Review the Flow Score evidence."
                )
            scores.combined.components[0].reason = scores.flow.reason
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
        prices = response.flow.liquidity.series
        latest = prices[-1]
        previous = prices[-2] if len(prices) >= 2 else None
        change = (
            latest.close_idr - previous.close_idr
            if previous and previous.close_idr > 0 and latest.close_idr > 0
            else None
        )
        company = Company(
            name=identity,
            sector=overview.sector if overview else None,
            sub_sector=overview.sub_sector if overview else None,
            last_close_idr=latest.close_idr,
            close_date=latest.date,
            previous_close_idr=previous.close_idr if previous else None,
            previous_close_date=previous.date if previous else None,
            change_idr=change,
            change_percent=(
                round(100 * change / previous.close_idr, 4)
                if change is not None and previous
                else None
            ),
        )
        points = []
        broker_periods = [
            ("5-day", response.flow.broker_summary_5d, "broker_top_5d"),
            ("20-day", response.flow.broker_summary, "broker_top"),
        ]
        scored_breadth = [
            (label, breadth, source_key)
            for label, summary, source_key in broker_periods
            if summary
            for breadth in summary.breadth
            if breadth.top_n in (3, 5)
        ]
        if scored_breadth:
            directions = {
                breadth.balance_ratio > 0
                for _, breadth, _ in scored_breadth
                if breadth.balance_ratio is not None
            }
            points.append(
                KeyPoint(
                    kind="conflict" if len(directions) > 1 else "evidence",
                    title="Broker balance by window",
                    text="Recent 5-day evidence carries 65% and 20-day evidence carries 35% of Broker Flow.",
                    items=[
                        f"{label} Top {breadth.top_n}: IDR {breadth.balance_idr:+,} across {breadth.buyer_count} buyers and {breadth.seller_count} sellers."
                        for label, breadth, _ in scored_breadth
                    ],
                    source_keys=list(
                        dict.fromkeys(source_key for _, _, source_key in scored_breadth)
                    ),
                )
            )
        foreign = response.flow.foreign_flow
        if foreign.net_inflow_idr is not None:
            points.append(
                KeyPoint(
                    kind="evidence",
                    title="Foreign investor flow",
                    text=f"Net IDR {foreign.net_inflow_idr:+,} across {len(foreign.series)} observations.",
                    items=[
                        f"{foreign.positive_days} positive-flow days and {foreign.negative_days} negative-flow days."
                    ],
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
                category="fundamental",
                text=(
                    "Financial reporting year: "
                    f"{fundamentals.reporting_period or 'unavailable'}."
                ),
                items=[
                    (
                        f"{group.label}: {group.score:.2f} / 100."
                        if group.score is not None
                        else f"{group.label}: not enough evidence to calculate."
                    )
                    for group in fundamentals.groups
                ],
                source_keys=[s.key for s in sources if s.key.startswith("company_")],
            )
        )
        if missing:
            points.append(
                KeyPoint(
                    kind="unavailable",
                    title="Incomplete evidence",
                    category="coverage",
                    text="Some evidence is unavailable. Check data availability for the affected sections and score limitations.",
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
