"""HTTP client for the Sectors Financial API v2."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping, Sequence
from queue import Empty, SimpleQueue
from threading import local
from typing import Any

import requests

from ..exceptions.sectors import (
    SectorsAuthenticationError,
    SectorsConfigurationError,
    SectorsNotFoundError,
    SectorsRateLimitError,
    SectorsResponseError,
    SectorsUpstreamError,
    SectorsValidationError,
)

logger = logging.getLogger(__name__)


class SectorsClient:
    """Retrieve raw JSON data from the Sectors API.

    Response normalization is intentionally deferred until representative
    response samples have been reviewed.
    """

    DEFAULT_BASE_URL = "https://api.sectors.app/v2/"
    DEFAULT_TIMEOUT = (5.0, 30.0)

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ) -> None:
        resolved_api_key = api_key or os.getenv("SECTORS_API_KEY")
        if not resolved_api_key:
            raise SectorsConfigurationError(
                "SECTORS_API_KEY is required to use SectorsClient."
            )

        self.base_url = f"{base_url.rstrip('/')}/"
        self.timeout = timeout
        self._headers = {
            "Authorization": resolved_api_key,
            "Accept": "application/json",
        }
        self.session = session
        self._thread_session = local()
        self._owned_sessions: SimpleQueue[requests.Session] = SimpleQueue()
        if session is not None:
            session.headers.update(self._headers)

    def _session_for_current_thread(self) -> requests.Session:
        if self.session is not None:
            return self.session

        session = getattr(self._thread_session, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update(self._headers)
            self._thread_session.session = session
            self._owned_sessions.put(session)
        return session

    def close(self) -> None:
        """Close the underlying HTTP session."""

        if self.session is not None:
            self.session.close()
        while True:
            try:
                self._owned_sessions.get_nowait().close()
            except Empty:
                break

    def __enter__(self) -> SectorsClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_free_float(
        self,
        *,
        sector: str | None = None,
        sub_sector: str | None = None,
        industry: str | None = None,
        sub_industry: str | None = None,
    ) -> Any:
        filters = {
            "sector": sector,
            "sub_sector": sub_sector,
            "industry": industry,
            "sub_industry": sub_industry,
        }
        selected_filters = [value for value in filters.values() if value is not None]
        if len(selected_filters) > 1:
            raise SectorsValidationError(
                "Free-float request accepts at most one classification filter."
            )
        return self._get("free-float/", filters)

    def get_daily(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> Any:
        return self._get(
            f"daily/{self._normalize_symbol(symbol)}/",
            {"start": start, "end": end},
        )

    def get_revenue_segments(
        self,
        symbol: str,
        *,
        financial_year: int | None = None,
    ) -> Any:
        return self._get(
            f"company/get-segments/{self._normalize_symbol(symbol)}/",
            {"financial_year": financial_year},
        )

    def get_company_report(
        self,
        symbol: str,
        *,
        sections: Sequence[str],
    ) -> Any:
        clean_sections = [section.strip() for section in sections if section.strip()]
        if not clean_sections:
            raise SectorsValidationError(
                "Company Report requires at least one explicit section."
            )
        return self._get(
            f"company/report/{self._normalize_symbol(symbol)}/",
            {"sections": ",".join(clean_sections)},
        )

    def get_shareholder_composition(
        self,
        symbol: str,
        *,
        year: int | None = None,
    ) -> Any:
        return self._get(
            f"company/shareholders-composition/{self._normalize_symbol(symbol)}/",
            {"year": year},
        )

    def get_broker_summary(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
        broker_code: str | None = None,
    ) -> Any:
        return self._get(
            f"broker-summary/{self._normalize_symbol(symbol)}/",
            {
                "start": start,
                "end": end,
                "broker_code": broker_code.upper() if broker_code else None,
            },
        )

    def get_top_brokers(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
        cohort: str | None = None,
        origin: str | None = None,
        foreign: bool | None = None,
        n_brokers: int | None = None,
    ) -> Any:
        if n_brokers is not None and not 1 <= n_brokers <= 90:
            raise SectorsValidationError("n_brokers must be between 1 and 90.")

        return self._get(
            f"broker-summary/{self._normalize_symbol(symbol)}/top/",
            {
                "start": start,
                "end": end,
                "cohort": cohort,
                "origin": origin,
                "foreign": str(foreign).lower() if foreign is not None else None,
                "n_brokers": n_brokers,
            },
        )

    def get_foreign_flow(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> Any:
        return self._get(
            f"foreign-flow/{self._normalize_symbol(symbol)}/",
            {"start": start, "end": end},
        )

    def _get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path.lstrip('/')}"
        clean_params = {
            key: value for key, value in (params or {}).items() if value is not None
        }

        logger.debug(
            "Requesting Sectors endpoint",
            extra={"sectors_path": path, "sectors_params": clean_params},
        )

        try:
            response = self._session_for_current_thread().get(
                url,
                params=clean_params,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            logger.warning(
                "Sectors request timed out",
                extra={"sectors_path": path},
            )
            raise SectorsUpstreamError("Sectors API request timed out.") from exc
        except requests.RequestException as exc:
            logger.warning(
                "Sectors request failed",
                extra={"sectors_path": path, "error_type": type(exc).__name__},
            )
            raise SectorsUpstreamError("Could not reach the Sectors API.") from exc

        if response.status_code >= 400:
            self._raise_for_status(response, path)

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as exc:
            logger.error(
                "Sectors returned invalid JSON",
                extra={
                    "sectors_path": path,
                    "upstream_status": response.status_code,
                },
            )
            raise SectorsResponseError(
                "Sectors API returned invalid JSON.",
                status_code=response.status_code,
            ) from exc

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper().removesuffix(".JK")
        if not re.fullmatch(r"[A-Z]{4}", normalized):
            raise SectorsValidationError("Symbol must contain four letters.")
        return normalized

    @staticmethod
    def _raise_for_status(response: requests.Response, path: str) -> None:
        status_code = response.status_code
        details: Any = None
        try:
            details = response.json()
        except requests.exceptions.JSONDecodeError:
            pass

        logger.warning(
            "Sectors returned an error response",
            extra={
                "sectors_path": path,
                "upstream_status": status_code,
            },
        )

        error_kwargs = {"status_code": status_code, "details": details}
        if status_code == 400:
            raise SectorsValidationError(
                "Sectors API rejected the request.", **error_kwargs
            )
        if status_code in {401, 403}:
            raise SectorsAuthenticationError(
                "Sectors API authentication failed.", **error_kwargs
            )
        if status_code == 404:
            raise SectorsNotFoundError("Sectors data was not found.", **error_kwargs)
        if status_code == 429:
            raise SectorsRateLimitError(
                "Sectors API rate or credit limit was reached.", **error_kwargs
            )
        raise SectorsUpstreamError(
            "Sectors API returned an unexpected error.", **error_kwargs
        )
