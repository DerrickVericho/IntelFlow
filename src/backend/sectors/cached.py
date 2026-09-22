"""Async typed boundary over the existing synchronous Sectors transport."""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Generic, TypeVar
from zoneinfo import ZoneInfo
from pydantic import TypeAdapter, ValidationError

from ..config import Settings
from ..cache.store import CacheStore
from ..schemas.transactions import DailyTransaction
from ..schemas.screeners import FreeFloat
from ..schemas.brokers import BrokerActivityList, TopBrokerList, ForeignFlowList
from ..schemas.company_reports import CompanyReportList
from ..schemas.detail_reports import ShareholderList, RevenueSegmentList
from ..exceptions.sectors import SectorsResponseError, SectorsValidationError

T = TypeVar("T")
logger = logging.getLogger(__name__)
ADAPTERS = {
    "get_daily": TypeAdapter(list[DailyTransaction]),
    "get_free_float": TypeAdapter(list[FreeFloat]),
    "get_broker_summary": TypeAdapter(BrokerActivityList),
    "get_top_brokers": TypeAdapter(TopBrokerList),
    "get_foreign_flow": TypeAdapter(ForeignFlowList),
    "get_company_report": TypeAdapter(CompanyReportList),
    "get_shareholder_composition": TypeAdapter(ShareholderList),
    "get_revenue_segments": TypeAdapter(RevenueSegmentList),
}


@dataclass(frozen=True)
class Retrieved(Generic[T]):
    data: T
    fetched_at: datetime


def canonical_key(prefix, operation, symbol, params):
    normalized = dict(params)
    if "sections" in normalized:
        normalized["sections"] = sorted(set(normalized["sections"]))
    if normalized.get("broker_code"):
        normalized["broker_code"] = normalized["broker_code"].upper()
    payload = json.dumps(
        [symbol.upper().removesuffix(".JK"), normalized], sort_keys=True, default=str
    )
    return f"{prefix}:{operation}:{hashlib.sha256(payload.encode()).hexdigest()}"


def ttl_for(settings: Settings, operation: str, params: dict, today: date):
    if operation == "get_company_report":
        dynamic = {"overview", "valuation"}.intersection(params["sections"])
        return (
            settings.cache_ttl_company_dynamic_seconds
            if dynamic
            else settings.cache_ttl_company_static_seconds
        )
    if operation == "get_shareholder_composition":
        return (
            90 * 86400
            if params.get("year", today.year) < today.year
            else settings.cache_ttl_shareholders_seconds
        )
    if operation == "get_free_float":
        return settings.cache_ttl_free_float_seconds
    if operation == "get_revenue_segments":
        return settings.cache_ttl_revenue_segments_seconds
    end = date.fromisoformat(params.get("end", today.isoformat()))
    # Yesterday may still receive delayed updates: only seal ranges after 7 days.
    return (
        settings.cache_ttl_market_historical_seconds
        if end < today - timedelta(days=7)
        else settings.cache_ttl_market_current_seconds
    )


class CachedSectorsGateway:
    def __init__(self, transport, store: CacheStore, settings: Settings):
        self.transport, self.store, self.settings = transport, store, settings
        # One session is never used concurrently. This also coalesces cache misses
        # within the single-worker MVP without an unbounded per-key lock registry.
        self.lock = asyncio.Lock()

    async def _get(self, operation, symbol="", **params):
        symbol = symbol.strip().upper().removesuffix(".JK")
        params = {k: v for k, v in params.items() if v is not None}
        today = datetime.now(ZoneInfo("Asia/Jakarta")).date()
        windows = {
            "get_daily": 30,
            "get_top_brokers": 90,
            "get_foreign_flow": 90,
            "get_broker_summary": 14,
        }
        if operation in windows:
            params.setdefault("end", today.isoformat())
            end = date.fromisoformat(params["end"])
            params.setdefault(
                "start", (end - timedelta(days=windows[operation] - 1)).isoformat()
            )
            start = date.fromisoformat(params["start"])
            if start > end or end > today:
                raise SectorsValidationError("Invalid effective request dates.")
            if operation == "get_broker_summary" and (end - start).days >= 14:
                raise SectorsValidationError(
                    "Broker activity requires chunks of at most 14 days."
                )
        if operation == "get_top_brokers":
            for k, v in {
                "origin": "all",
                "cohort": "all",
                "foreign": False,
                "n_brokers": 10,
            }.items():
                params.setdefault(k, v)
        if operation == "get_shareholder_composition":
            params.setdefault("year", today.year)
        if "sections" in params:
            params["sections"] = sorted(set(params["sections"]))
            if not params["sections"]:
                raise SectorsValidationError(
                    "Company Report requires explicit sections."
                )
        key = canonical_key(self.settings.redis_key_prefix, operation, symbol, params)
        adapter = ADAPTERS[operation]
        async with self.lock:
            cached = await self.store.get(key)
            if cached is not None:
                try:
                    entry = json.loads(cached)
                    data = adapter.validate_python(entry["payload"])
                    stamp = datetime.fromisoformat(entry["fetched_at"])
                    if stamp.tzinfo is None:
                        raise ValueError("Missing cache timezone")
                    self._check_identity(data, symbol)
                    self._check_request(data, operation, params)
                    logger.info(
                        "Sectors cache",
                        extra={"operation": operation, "cache_outcome": "hit"},
                    )
                    return Retrieved(data, stamp)
                except (ValueError, KeyError, TypeError, SectorsResponseError):
                    logger.warning(
                        "Invalid cache entry",
                        extra={"operation": operation, "cache_outcome": "invalid"},
                    )
            method = getattr(self.transport, operation)
            args = (symbol,) if symbol else ()
            raw = await asyncio.to_thread(method, *args, **params)
            try:
                data = adapter.validate_python(raw)
                self._check_identity(data, symbol)
                self._check_request(data, operation, params)
            except ValidationError as exc:
                raise SectorsResponseError(f"Invalid {operation} payload.") from exc
            stamp = datetime.now(UTC)
            try:
                entry = json.dumps(
                    {"fetched_at": stamp.isoformat(), "payload": raw}, allow_nan=False
                )
            except (ValueError, TypeError) as exc:
                raise SectorsResponseError(
                    "Upstream payload contains invalid JSON numeric values."
                ) from exc
            await self.store.set(
                key, entry, ttl_for(self.settings, operation, params, stamp.date())
            )
            logger.info(
                "Sectors cache", extra={"operation": operation, "cache_outcome": "miss"}
            )
            return Retrieved(data, stamp)

    @staticmethod
    def _check_request(data, operation, params):
        if operation == "get_top_brokers":
            if (
                data.start.isoformat() != params["start"]
                or data.end.isoformat() != params["end"]
            ):
                raise SectorsResponseError(
                    "Broker ranking range does not match request."
                )
            for name in ("origin", "cohort", "foreign"):
                if getattr(data, name) != params[name]:
                    raise SectorsResponseError(
                        "Broker ranking filters do not match request."
                    )
        if operation == "get_shareholder_composition" and data.year != params["year"]:
            raise SectorsResponseError(
                "Shareholder response year does not match request."
            )

    @staticmethod
    def _check_identity(data, symbol):
        if not symbol:
            return
        rows = data if isinstance(data, list) else [data]
        if any(row.symbol.upper().removesuffix(".JK") != symbol for row in rows):
            raise SectorsResponseError("Upstream symbol does not match request.")

    async def get_daily(self, symbol, **params) -> Retrieved[list[DailyTransaction]]:
        return await self._get("get_daily", symbol, **params)

    async def get_top_brokers(self, symbol, **params) -> Retrieved[TopBrokerList]:
        return await self._get("get_top_brokers", symbol, **params)

    async def get_foreign_flow(self, symbol, **params) -> Retrieved[ForeignFlowList]:
        return await self._get("get_foreign_flow", symbol, **params)

    async def get_company_report(
        self, symbol, **params
    ) -> Retrieved[CompanyReportList]:
        return await self._get("get_company_report", symbol, **params)

    async def get_broker_summary(
        self, symbol, **params
    ) -> Retrieved[BrokerActivityList]:
        return await self._get("get_broker_summary", symbol, **params)

    async def get_shareholder_composition(
        self, symbol, **params
    ) -> Retrieved[ShareholderList]:
        return await self._get("get_shareholder_composition", symbol, **params)

    async def get_free_float(self, **params) -> Retrieved[list[FreeFloat]]:
        return await self._get("get_free_float", **params)

    async def get_revenue_segments(
        self, symbol, **params
    ) -> Retrieved[RevenueSegmentList]:
        return await self._get("get_revenue_segments", symbol, **params)
