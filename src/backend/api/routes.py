"""Thin HTTP adapters; business calculations belong to the service."""

from typing import Annotated, Literal
from fastapi import APIRouter, Depends, Query, Request
from ..schemas.broker_flow import BrokerFlowResponse
from ..schemas.brokers import BrokerResponse
from ..schemas.flow import FlowResponse
from ..schemas.prices import PriceResponse
from ..schemas.research import ResearchResponse
from ..schemas.shareholders import ShareholderResponse
from ..services.research import ResearchService

router = APIRouter(prefix="/api/v1/stocks", tags=["research"])


def get_service(request: Request) -> ResearchService:
    return request.app.state.research


Service = Annotated[ResearchService, Depends(get_service)]


@router.get("/{symbol}/intel-score", response_model=ResearchResponse)
async def research(symbol: str, service: Service) -> ResearchResponse:
    return await service.research(symbol)


@router.get("/{symbol}/flow", response_model=FlowResponse)
async def flow(
    symbol: str, service: Service, window: Literal["1d", "5d", "20d"] = Query(...)
) -> FlowResponse:
    return await service.flow(symbol, window)


@router.get("/{symbol}/price-history", response_model=PriceResponse)
async def prices(
    symbol: str, service: Service, range: Literal["1w", "1m", "3m"] = Query(...)
) -> PriceResponse:
    return await service.prices(symbol, range)


@router.get("/{symbol}/shareholders", response_model=ShareholderResponse)
async def shareholders(
    symbol: str,
    service: Service,
    year: int | None = Query(None),
) -> ShareholderResponse:
    return await service.shareholders(symbol, year)


@router.get("/{symbol}/broker-series", response_model=BrokerResponse)
async def brokers(
    symbol: str,
    service: Service,
    range: Literal["1w", "1m", "3m"] = Query(...),
    brokers: str | None = Query(None, max_length=29),
) -> BrokerResponse:
    return await service.brokers(symbol, range, brokers)


@router.get("/{symbol}/broker-flow", response_model=BrokerFlowResponse)
async def broker_flow(
    symbol: str,
    service: Service,
    range: Literal["5d", "1m", "3m"] = Query(...),
) -> BrokerFlowResponse:
    return await service.broker_flow(symbol, range)
