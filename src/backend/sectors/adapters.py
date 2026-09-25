"""Pydantic adapters for every supported Sectors operation."""

from typing import Any

from pydantic import TypeAdapter

from .schemas.brokers import BrokerActivityList, ForeignFlowList, TopBrokerList
from .schemas.company_reports import CompanyReportList
from .schemas.detail_reports import RevenueSegmentList, ShareholderList
from .schemas.screeners import FreeFloat
from .schemas.transactions import DailyTransaction
from .types import Operation

DAILY_ADAPTER = TypeAdapter(list[DailyTransaction])
FREE_FLOAT_ADAPTER = TypeAdapter(list[FreeFloat])
BROKER_SUMMARY_ADAPTER = TypeAdapter(BrokerActivityList)
TOP_BROKERS_ADAPTER = TypeAdapter(TopBrokerList)
FOREIGN_FLOW_ADAPTER = TypeAdapter(ForeignFlowList)
COMPANY_REPORT_ADAPTER = TypeAdapter(CompanyReportList)
SHAREHOLDERS_ADAPTER = TypeAdapter(ShareholderList)
REVENUE_SEGMENTS_ADAPTER = TypeAdapter(RevenueSegmentList)


# The registry is useful for generic tooling and provider-schema checks. The
# gateway methods use the named adapters above so their return types stay clear.
ADAPTERS: dict[Operation, TypeAdapter[Any]] = {
    "get_daily": DAILY_ADAPTER,
    "get_free_float": FREE_FLOAT_ADAPTER,
    "get_broker_summary": BROKER_SUMMARY_ADAPTER,
    "get_top_brokers": TOP_BROKERS_ADAPTER,
    "get_foreign_flow": FOREIGN_FLOW_ADAPTER,
    "get_company_report": COMPANY_REPORT_ADAPTER,
    "get_shareholder_composition": SHAREHOLDERS_ADAPTER,
    "get_revenue_segments": REVENUE_SEGMENTS_ADAPTER,
}
