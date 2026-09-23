"""Date boundary for Sectors market-data requests."""

from datetime import UTC, date, datetime


def latest_provider_date(local_date: date, utc_date: date | None = None) -> date:
    """Never send a Jakarta calendar date that is still in the UTC future."""

    return min(local_date, utc_date or datetime.now(UTC).date())
