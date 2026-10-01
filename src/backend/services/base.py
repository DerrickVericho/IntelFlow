"""Shared provider access and date helpers for research use cases."""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta
from typing import TypeVar
from zoneinfo import ZoneInfo

from ..exceptions.research import DataNotFoundError
from ..exceptions.sectors import SectorsError
from ..models.common import MissingInput
from ..sectors.gateway import SectorsGateway
from ..sectors.schemas.transactions import DailyTransaction
from ..sectors.types import Retrieved
from ..sectors.utils import latest_provider_date
from .utils import unique_rows

logger = logging.getLogger(__name__)
T = TypeVar("T")


class ServiceBase:
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
            missing.append(
                MissingInput(
                    key=key,
                    reason="This source could not be retrieved from Sectors.",
                )
            )
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
