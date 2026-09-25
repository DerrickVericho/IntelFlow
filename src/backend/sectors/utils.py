"""Pure helpers for Sectors request preparation and cache validation."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any, TypeVar

from pydantic import TypeAdapter, ValidationError

from ..config import Settings
from ..exceptions.sectors import SectorsResponseError, SectorsValidationError
from .types import Operation, Retrieved

T = TypeVar("T")

MARKET_WINDOWS: dict[Operation, int] = {
    "get_daily": 30,
    "get_top_brokers": 90,
    "get_foreign_flow": 90,
    "get_broker_summary": 14,
}


def latest_provider_date(local_date: date, utc_date: date | None = None) -> date:
    """Return a date that is current in both Jakarta and UTC."""

    return min(local_date, utc_date or datetime.now(UTC).date())


def prepare_request(
    operation: Operation,
    symbol: str,
    params: dict[str, Any],
    *,
    local_today: date,
    provider_today: date,
) -> tuple[str, dict[str, Any]]:
    """Normalize identifiers, apply defaults, and reject invalid parameters."""

    normalized_symbol = symbol.strip().upper().removesuffix(".JK")
    normalized_params = {
        key: value for key, value in params.items() if value is not None
    }

    if operation in MARKET_WINDOWS:
        normalized_params.setdefault("end", provider_today.isoformat())

        try:
            end = date.fromisoformat(normalized_params["end"])
        except (TypeError, ValueError) as exc:
            raise SectorsValidationError("End date must use YYYY-MM-DD.") from exc

        default_days = MARKET_WINDOWS[operation]
        normalized_params.setdefault(
            "start",
            (end - timedelta(days=default_days - 1)).isoformat(),
        )

        try:
            start = date.fromisoformat(normalized_params["start"])
        except (TypeError, ValueError) as exc:
            raise SectorsValidationError("Start date must use YYYY-MM-DD.") from exc

        if start > end or end > provider_today:
            raise SectorsValidationError("Invalid effective request dates.")

        if operation == "get_broker_summary" and (end - start).days >= 14:
            raise SectorsValidationError(
                "Broker activity requires chunks of at most 14 days."
            )

    if operation == "get_top_brokers":
        defaults = {
            "origin": "all",
            "cohort": "all",
            "foreign": False,
            "n_brokers": 10,
        }
        for key, value in defaults.items():
            normalized_params.setdefault(key, value)

    if operation == "get_shareholder_composition":
        normalized_params.setdefault("year", local_today.year)

    if "sections" in normalized_params:
        normalized_params["sections"] = sorted(set(normalized_params["sections"]))
        if not normalized_params["sections"]:
            raise SectorsValidationError("Company Report requires explicit sections.")

    return normalized_symbol, normalized_params


def canonical_key(
    prefix: str,
    operation: Operation,
    symbol: str,
    params: dict[str, Any],
) -> str:
    """Build one stable Redis key for semantically equivalent requests."""

    normalized_params = dict(params)

    if "sections" in normalized_params:
        normalized_params["sections"] = sorted(set(normalized_params["sections"]))

    if normalized_params.get("broker_code"):
        normalized_params["broker_code"] = normalized_params["broker_code"].upper()

    identity = [
        symbol.upper().removesuffix(".JK"),
        normalized_params,
    ]
    payload = json.dumps(identity, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode()).hexdigest()

    return f"{prefix}:{operation}:{digest}"


def ttl_for(
    settings: Settings,
    operation: Operation,
    params: dict[str, Any],
    today: date,
) -> int:
    """Select cache lifetime from the kind and age of provider data."""

    if operation == "get_company_report":
        dynamic_sections = {"overview", "valuation"}.intersection(params["sections"])
        if dynamic_sections:
            return settings.cache_ttl_company_dynamic_seconds
        return settings.cache_ttl_company_static_seconds

    if operation == "get_shareholder_composition":
        if params.get("year", today.year) < today.year:
            return 90 * 86400
        return settings.cache_ttl_shareholders_seconds

    if operation == "get_free_float":
        return settings.cache_ttl_free_float_seconds

    if operation == "get_revenue_segments":
        return settings.cache_ttl_revenue_segments_seconds

    end = date.fromisoformat(params.get("end", today.isoformat()))
    if end < today - timedelta(days=7):
        return settings.cache_ttl_market_historical_seconds

    return settings.cache_ttl_market_current_seconds


def validate_payload(
    raw: Any,
    adapter: TypeAdapter[T],
    operation: Operation,
    symbol: str,
    params: dict[str, Any],
) -> T:
    """Parse provider JSON and verify that it belongs to the request."""

    try:
        data = adapter.validate_python(raw)
    except ValidationError as exc:
        raise SectorsResponseError(f"Invalid {operation} payload.") from exc

    _check_identity(data, symbol)
    _check_request(data, operation, params)

    return data


def restore_cached(
    cached: str,
    adapter: TypeAdapter[T],
    operation: Operation,
    symbol: str,
    params: dict[str, Any],
) -> Retrieved[T]:
    """Restore and revalidate a raw provider payload stored in Redis."""

    entry = json.loads(cached)
    data = validate_payload(entry["payload"], adapter, operation, symbol, params)
    fetched_at = datetime.fromisoformat(entry["fetched_at"])

    if fetched_at.tzinfo is None:
        raise ValueError("Missing cache timezone")

    return Retrieved(data=data, fetched_at=fetched_at)


def serialize_cached(raw: Any, fetched_at: datetime) -> str:
    """Serialize a complete raw provider payload without allowing NaN values."""

    try:
        return json.dumps(
            {"fetched_at": fetched_at.isoformat(), "payload": raw},
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SectorsResponseError(
            "Upstream payload contains invalid JSON numeric values."
        ) from exc


def _check_identity(data: Any, symbol: str) -> None:
    if not symbol:
        return

    rows = data if isinstance(data, list) else [data]
    has_wrong_symbol = any(
        row.symbol.upper().removesuffix(".JK") != symbol for row in rows
    )

    if has_wrong_symbol:
        raise SectorsResponseError("Upstream symbol does not match request.")


def _check_request(
    data: Any,
    operation: Operation,
    params: dict[str, Any],
) -> None:
    if operation == "get_top_brokers":
        dates_match = (
            data.start.isoformat() == params["start"]
            and data.end.isoformat() == params["end"]
        )
        if not dates_match:
            raise SectorsResponseError("Broker ranking range does not match request.")

        for name in ("origin", "cohort", "foreign"):
            if getattr(data, name) != params[name]:
                raise SectorsResponseError(
                    "Broker ranking filters do not match request."
                )

    if operation == "get_shareholder_composition":
        if data.year != params["year"]:
            raise SectorsResponseError(
                "Shareholder response year does not match request."
            )
