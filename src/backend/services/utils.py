"""Pure helpers shared by backend research use cases."""

import re
from collections.abc import Iterable, Sequence
from datetime import date, timedelta
from typing import Any, Literal, Protocol, TypeVar

from ..exceptions.research import InvalidRangeError, InvalidSymbolError
from ..exceptions.sectors import SectorsResponseError
from ..models.common import MissingInput, Source
from ..sectors.types import Retrieved


class Dated(Protocol):
    date: date


DatedT = TypeVar("DatedT", bound=Dated)
ResearchStatus = Literal["complete", "partial", "stale"]


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper().removesuffix(".JK")
    if not re.fullmatch(r"[A-Z]{4}", normalized):
        raise InvalidSymbolError("Use a four-letter IDX ticker, for example BBCA.")
    return normalized


def unique_rows(rows: Iterable[DatedT]) -> list[DatedT]:
    rows_by_date: dict[date, DatedT] = {}
    for row in rows:
        if row.date in rows_by_date and row != rows_by_date[row.date]:
            raise SectorsResponseError(
                "Conflicting upstream observations for the same date."
            )
        rows_by_date[row.date] = row

    return sorted(rows_by_date.values(), key=lambda row: row.date)


def source_record(
    key: str,
    result: Retrieved[Any],
    *,
    today: date,
    as_of: date | None = None,
    start: date | None = None,
    end: date | None = None,
    period: str | None = None,
    max_age: int = 7,
) -> Source:
    return Source(
        key=key,
        as_of=as_of,
        period=period,
        fetched_at=result.fetched_at,
        effective_start=start,
        effective_end=end,
        is_stale=as_of is not None and (today - as_of).days > max_age,
    )


def research_status(
    missing: Sequence[MissingInput],
    sources: Sequence[Source],
) -> ResearchStatus:
    if missing:
        return "partial"
    if any(source.is_stale for source in sources):
        return "stale"
    return "complete"


def market_range(range_name: str, end: date) -> tuple[date, date]:
    days = {"1w": 7, "1m": 30, "3m": 90}.get(range_name)
    if days is None:
        raise InvalidRangeError("Range must be 1w, 1m, or 3m.")
    return end - timedelta(days=days - 1), end
