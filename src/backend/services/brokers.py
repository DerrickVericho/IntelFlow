"""Broker selection and dated net activity series."""

import re
from datetime import timedelta

from ..exceptions.research import InvalidBrokersError, ResearchUnavailableError
from ..models.common import MissingInput
from ..schemas.brokers import BrokerPoint, BrokerResponse, BrokerSeries
from .base import ServiceBase
from .utils import (
    market_range,
    normalize_symbol,
    research_status,
    source_record,
    unique_rows,
)


class BrokerSeriesService(ServiceBase):
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
