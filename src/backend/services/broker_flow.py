"""Period-ranked brokers, aligned price candles, and daily broker quantities."""

from datetime import date, timedelta

from ..exceptions.research import DataNotFoundError, InvalidRangeError
from ..models.common import MissingInput
from ..schemas.broker_flow import (
    BrokerFlowDay,
    BrokerFlowPoint,
    BrokerFlowRank,
    BrokerFlowResponse,
    BrokerFlowSeries,
    DailyBrokerQuantity,
)
from ..schemas.prices import PricePoint
from ..sectors.schemas.brokers import BrokerActivitySymbolDetails
from ..sectors.schemas.transactions import DailyTransaction
from .base import ServiceBase
from .utils import (
    normalize_symbol,
    research_status,
    source_record,
    unique_rows,
)


def _has_traded_candle(row: DailyTransaction) -> bool:
    if row.volume <= 0 or row.open is None or row.high is None or row.low is None:
        return False
    return (
        row.open > 0
        and row.close > 0
        and row.low > 0
        and row.low <= min(row.open, row.close)
        and row.high >= max(row.open, row.close)
    )


def _daily_top(
    rows: list[BrokerActivitySymbolDetails], price_dates: list[date]
) -> list[BrokerFlowDay]:
    by_date = {row.date: row for row in rows}
    days: list[BrokerFlowDay] = []
    for trading_date in price_dates:
        row = by_date.get(trading_date)
        if row is None:
            days.append(
                BrokerFlowDay(
                    date=trading_date, available=False, top_buyers=[], top_sellers=[]
                )
            )
            continue
        buyers = sorted(
            (broker for broker in row.summary if broker.nlot > 0),
            key=lambda broker: (-broker.nlot, broker.broker_code),
        )[:5]
        sellers = sorted(
            (broker for broker in row.summary if broker.nlot < 0),
            key=lambda broker: (broker.nlot, broker.broker_code),
        )[:5]
        days.append(
            BrokerFlowDay(
                date=trading_date,
                available=True,
                top_buyers=[
                    DailyBrokerQuantity(
                        broker_code=broker.broker_code, shares=broker.nlot * 100
                    )
                    for broker in buyers
                ],
                top_sellers=[
                    DailyBrokerQuantity(
                        broker_code=broker.broker_code, shares=-broker.nlot * 100
                    )
                    for broker in sellers
                ],
            )
        )
    return days


def _series(
    ranks: list[BrokerFlowRank],
    side: str,
    rows: list[BrokerActivitySymbolDetails],
    price_dates: list[date],
) -> list[BrokerFlowSeries]:
    daily = {
        row.date: {broker.broker_code: broker for broker in row.summary} for row in rows
    }
    series = []
    for ranked in ranks:
        cumulative = 0
        points = []
        for trading_date in price_dates:
            day = daily.get(trading_date)
            if day is None:
                points.append(
                    BrokerFlowPoint(
                        date=trading_date,
                        net_shares=None,
                        cumulative_net_shares=None,
                    )
                )
                continue
            # A broker absent from a reported day had no reported activity.
            broker = day.get(ranked.broker_code)
            net_shares = broker.nlot * 100 if broker else 0
            cumulative += net_shares
            points.append(
                BrokerFlowPoint(
                    date=trading_date,
                    net_shares=net_shares,
                    cumulative_net_shares=cumulative,
                )
            )
        series.append(
            BrokerFlowSeries(broker_code=ranked.broker_code, side=side, points=points)
        )
    return series


class BrokerFlowService(ServiceBase):
    async def broker_flow(self, symbol: str, range_: str) -> BrokerFlowResponse:
        symbol = normalize_symbol(symbol)
        # Validate before the first paid request.
        if range_ not in {"5d", "1m", "3m"}:
            raise InvalidRangeError("Range must be 5d, 1m, or 3m.")

        market_end = self._market_end()
        price_result, history = await self._history(symbol, end=market_end)
        target_sessions = {"5d": 5, "1m": 20, "3m": 60}[range_]
        prices = [row for row in history if _has_traded_candle(row)][-target_sessions:]
        if not prices:
            raise DataNotFoundError("No traded price candles in the selected period.")
        start, end = prices[0].date, prices[-1].date
        price_dates = [row.date for row in prices]
        excluded_price_dates = [
            row.date
            for row in history
            if row.date >= start and not _has_traded_candle(row)
        ]
        missing: list[MissingInput] = []
        source = source_record(
            "daily", price_result, today=self.today(), as_of=end, start=start, end=end
        )
        sources = [source]
        incomplete_history = len(prices) < target_sessions
        if incomplete_history:
            missing.append(
                MissingInput(
                    key="broker_flow.prices",
                    reason=f"Only {len(prices)} of {target_sessions} trading sessions were returned.",
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
                n_brokers=5,
            ),
            "broker_flow.top",
            missing,
        )
        buyers: list[BrokerFlowRank] = []
        sellers: list[BrokerFlowRank] = []
        if top is not None:
            if top.data.start != start or top.data.end != end:
                missing.append(
                    MissingInput(
                        key="broker_flow.top",
                        reason="Broker ranking dates differ from price dates.",
                    )
                )
            else:
                buyers = [
                    BrokerFlowRank(
                        rank=row.rank, broker_code=row.broker_code, net_idr=row.net_idr
                    )
                    for row in top.data.top_buyers[:5]
                ]
                sellers = [
                    BrokerFlowRank(
                        rank=row.rank, broker_code=row.broker_code, net_idr=row.net_idr
                    )
                    for row in top.data.top_sellers[:5]
                ]
                sources.append(
                    source_record(
                        "broker_flow.top",
                        top,
                        today=self.today(),
                        as_of=end,
                        start=start,
                        end=end,
                    )
                )
                if not buyers and not sellers:
                    missing.append(
                        MissingInput(
                            key="broker_flow.top",
                            reason="No ranked brokers were returned for this period.",
                        )
                    )

        rows: list[BrokerActivitySymbolDetails] = []
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + timedelta(days=13), end)
            key = "broker_flow.daily." + cursor.isoformat()
            result = await self._optional(
                self.gateway.get_broker_summary(
                    symbol, start=cursor.isoformat(), end=chunk_end.isoformat()
                ),
                key,
                missing,
            )
            if result is not None:
                chunk = [
                    row for row in result.data.data if cursor <= row.date <= chunk_end
                ]
                rows.extend(chunk)
                record = source_record(
                    key,
                    result,
                    today=self.today(),
                    as_of=max((row.date for row in chunk), default=None),
                    start=cursor,
                    end=chunk_end,
                )
                if chunk_end < end - timedelta(days=7):
                    record.is_stale = False
                sources.append(record)
            cursor = chunk_end + timedelta(days=1)

        rows = unique_rows(rows)
        covered = {row.date for row in rows}
        if any(day not in covered for day in price_dates):
            missing.append(
                MissingInput(
                    key="broker_flow.daily",
                    reason="Daily broker activity is missing for some price dates.",
                )
            )
        return BrokerFlowResponse(
            symbol=symbol,
            as_of=end,
            status=research_status(missing, sources),
            sources=sources,
            missing_inputs=missing,
            range=range_,
            effective_start=start,
            effective_end=end,
            incomplete_history=incomplete_history,
            excluded_price_dates=excluded_price_dates,
            prices=[PricePoint(**row.model_dump(exclude={"symbol"})) for row in prices],
            top_buyers=buyers,
            top_sellers=sellers,
            broker_series=_series(buyers, "buyer", rows, price_dates)
            + _series(sellers, "seller", rows, price_dates),
            days=_daily_top(rows, price_dates),
        )
