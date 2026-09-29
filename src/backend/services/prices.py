"""Dated OHLC and volume history."""

from ..models.common import MissingInput
from ..schemas.prices import PricePoint, PriceResponse
from .base import ServiceBase
from .utils import market_range, normalize_symbol, research_status, source_record


class PriceHistoryService(ServiceBase):
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
