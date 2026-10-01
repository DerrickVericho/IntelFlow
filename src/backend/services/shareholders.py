"""Monthly shareholder composition history."""

from ..exceptions.research import InvalidYearError
from ..exceptions.sectors import SectorsNotFoundError
from ..models.common import MissingInput
from ..schemas.shareholders import Category, ShareholderPoint, ShareholderResponse
from .base import ServiceBase
from .utils import normalize_symbol, research_status, source_record, unique_rows


class ShareholderService(ServiceBase):
    async def shareholders(
        self,
        symbol: str,
        year: int | None = None,
    ) -> ShareholderResponse:
        symbol = normalize_symbol(symbol)
        year = year if year is not None else self.today().year
        if not 2021 <= year <= self.today().year:
            raise InvalidYearError("Year must be between 2021 and the current year.")
        try:
            result = await self.gateway.get_shareholder_composition(symbol, year=year)
        except SectorsNotFoundError:
            # A missing symbol/year dataset is an empty research result, not an
            # invalid client request. Other provider failures still surface.
            result = None
        rows = (
            unique_rows([r for r in result.data.data if r.date.year == year])
            if result
            else []
        )
        categories = (
            [
                k
                for k in type(rows[0]).model_fields
                if k.endswith(("_l", "_f")) and not k.startswith("total_")
            ]
            if rows
            else []
        )
        points = [
            ShareholderPoint(
                date=r.date,
                shares_number=r.shares_number,
                holdings={k: getattr(r, k) for k in categories},
                total_local=r.total_l,
                total_foreign=r.total_f,
                shareholder_count=r.numbers_of_shareholders,
                shareholder_count_change=r.change_in_shareholders,
            )
            for r in rows
        ]
        source = (
            source_record(
                "shareholders",
                result,
                today=self.today(),
                as_of=rows[-1].date if rows else None,
                max_age=75,
            )
            if result
            else None
        )
        if source and year < self.today().year:
            source.is_stale = False
        missing = (
            []
            if rows
            else [
                MissingInput(
                    key="shareholders",
                    reason="No shareholder snapshots for this symbol and year",
                )
            ]
        )
        if rows and any(
            row.numbers_of_shareholders is None or row.change_in_shareholders is None
            for row in rows
        ):
            missing.append(
                MissingInput(
                    key="shareholders.count",
                    reason="Some monthly shareholder counts or changes were not reported",
                )
            )
        return ShareholderResponse(
            symbol=symbol,
            as_of=source.as_of if source else None,
            status=research_status(missing, [source] if source else []),
            sources=[source] if source else [],
            missing_inputs=missing,
            year=year,
            supported_years=list(range(2021, self.today().year + 1)),
            categories=[
                Category(
                    key=k,
                    label=k[:-2].replace("_", " ").title()
                    + (" Local" if k.endswith("_l") else " Foreign"),
                )
                for k in categories
            ],
            series=points,
        )
