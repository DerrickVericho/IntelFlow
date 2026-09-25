"""Cache-first, validated implementation of the Sectors gateway."""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any, TypeVar
from zoneinfo import ZoneInfo

from pydantic import TypeAdapter

from ..cache.store import CacheStore
from ..config import Settings
from ..exceptions.sectors import SectorsResponseError
from .adapters import (
    BROKER_SUMMARY_ADAPTER,
    COMPANY_REPORT_ADAPTER,
    DAILY_ADAPTER,
    FOREIGN_FLOW_ADAPTER,
    FREE_FLOAT_ADAPTER,
    REVENUE_SEGMENTS_ADAPTER,
    SHAREHOLDERS_ADAPTER,
    TOP_BROKERS_ADAPTER,
)
from .schemas.brokers import BrokerActivityList, ForeignFlowList, TopBrokerList
from .schemas.company_reports import CompanyReportList
from .schemas.detail_reports import RevenueSegmentList, ShareholderList
from .schemas.screeners import FreeFloat
from .schemas.transactions import DailyTransaction
from .types import Operation, Retrieved
from .utils import (
    canonical_key,
    latest_provider_date,
    prepare_request,
    restore_cached,
    serialize_cached,
    ttl_for,
    validate_payload,
)

T = TypeVar("T")
logger = logging.getLogger(__name__)


class CachedSectorsGateway:
    """Return validated Sectors data from Redis or the upstream transport."""

    def __init__(
        self,
        transport: Any,
        store: CacheStore,
        settings: Settings,
        utc_today: Callable[[], date] | None = None,
    ) -> None:
        self.transport = transport
        self.store = store
        self.settings = settings
        self.utc_today = utc_today or (lambda: datetime.now(UTC).date())

        # The requests Session is synchronous and shared. This lock also merges
        # equivalent cache misses while the MVP runs as one application worker.
        self.lock = asyncio.Lock()

    async def _get(
        self,
        operation: Operation,
        adapter: TypeAdapter[T],
        fetch: Callable[..., Any],
        *,
        symbol: str = "",
        params: dict[str, Any] | None = None,
    ) -> Retrieved[T]:
        local_today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
        provider_today = latest_provider_date(local_today, self.utc_today())
        symbol, params = prepare_request(
            operation,
            symbol,
            params or {},
            local_today=local_today,
            provider_today=provider_today,
        )

        key = canonical_key(
            self.settings.redis_key_prefix,
            operation,
            symbol,
            params,
        )

        async with self.lock:
            cached = await self.store.get(key)
            if cached is not None:
                try:
                    result = restore_cached(
                        cached,
                        adapter,
                        operation,
                        symbol,
                        params,
                    )
                except (KeyError, TypeError, ValueError, SectorsResponseError):
                    logger.warning(
                        "Invalid cache entry",
                        extra={
                            "operation": operation,
                            "cache_outcome": "invalid",
                        },
                    )
                else:
                    logger.info(
                        "Sectors cache",
                        extra={
                            "operation": operation,
                            "cache_outcome": "hit",
                        },
                    )
                    return result

            args = (symbol,) if symbol else ()
            raw = await asyncio.to_thread(fetch, *args, **params)
            data = validate_payload(raw, adapter, operation, symbol, params)
            fetched_at = datetime.now(UTC)
            entry = serialize_cached(raw, fetched_at)

            await self.store.set(
                key,
                entry,
                ttl_for(self.settings, operation, params, fetched_at.date()),
            )

            logger.info(
                "Sectors cache",
                extra={
                    "operation": operation,
                    "cache_outcome": "miss",
                },
            )

            return Retrieved(data=data, fetched_at=fetched_at)

    async def get_daily(
        self,
        symbol: str,
        **params: Any,
    ) -> Retrieved[list[DailyTransaction]]:
        return await self._get(
            "get_daily",
            DAILY_ADAPTER,
            self.transport.get_daily,
            symbol=symbol,
            params=params,
        )

    async def get_top_brokers(
        self,
        symbol: str,
        **params: Any,
    ) -> Retrieved[TopBrokerList]:
        return await self._get(
            "get_top_brokers",
            TOP_BROKERS_ADAPTER,
            self.transport.get_top_brokers,
            symbol=symbol,
            params=params,
        )

    async def get_foreign_flow(
        self,
        symbol: str,
        **params: Any,
    ) -> Retrieved[ForeignFlowList]:
        return await self._get(
            "get_foreign_flow",
            FOREIGN_FLOW_ADAPTER,
            self.transport.get_foreign_flow,
            symbol=symbol,
            params=params,
        )

    async def get_company_report(
        self,
        symbol: str,
        **params: Any,
    ) -> Retrieved[CompanyReportList]:
        return await self._get(
            "get_company_report",
            COMPANY_REPORT_ADAPTER,
            self.transport.get_company_report,
            symbol=symbol,
            params=params,
        )

    async def get_broker_summary(
        self,
        symbol: str,
        **params: Any,
    ) -> Retrieved[BrokerActivityList]:
        return await self._get(
            "get_broker_summary",
            BROKER_SUMMARY_ADAPTER,
            self.transport.get_broker_summary,
            symbol=symbol,
            params=params,
        )

    async def get_shareholder_composition(
        self,
        symbol: str,
        **params: Any,
    ) -> Retrieved[ShareholderList]:
        return await self._get(
            "get_shareholder_composition",
            SHAREHOLDERS_ADAPTER,
            self.transport.get_shareholder_composition,
            symbol=symbol,
            params=params,
        )

    async def get_free_float(
        self,
        **params: Any,
    ) -> Retrieved[list[FreeFloat]]:
        return await self._get(
            "get_free_float",
            FREE_FLOAT_ADAPTER,
            self.transport.get_free_float,
            params=params,
        )

    async def get_revenue_segments(
        self,
        symbol: str,
        **params: Any,
    ) -> Retrieved[RevenueSegmentList]:
        return await self._get(
            "get_revenue_segments",
            REVENUE_SEGMENTS_ADAPTER,
            self.transport.get_revenue_segments,
            symbol=symbol,
            params=params,
        )
