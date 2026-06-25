"""
Pruebas unitarias para el path use_mocks=True en analytics_service.

Verifica que cuando use_mocks=True cada función delegue a mock_data
sin tocar la base de datos (db.execute no debe ser llamado).
"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.services.analytics_service import (
    get_average_ticket,
    get_delivery_performance,
    get_orders_by_status,
    get_peak_hours,
    get_sales_report,
    get_top_products,
)


@pytest.fixture
def mock_db():
    """Base de datos simulada que no debe ser invocada en el path de mocks."""
    db = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# get_sales_report con use_mocks=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sales_report_usa_mock_data(mock_db):
    """Con use_mocks=True debe delegar a mock_data.sales_report sin consultar la BD."""
    from app.schemas.responses import SalesReport, SalesPeriod

    valor_mock = SalesReport(
        period=SalesPeriod(**{"from": None, "to": None}),
        totalSales=87_320_000,
        totalOrders=1_148,
        currency="CLP",
    )
    with patch(
        "app.services.analytics_service.mock_data.sales_report",
        return_value=valor_mock,
    ) as mock_fn:
        result = await get_sales_report(mock_db, None, None, use_mocks=True)

    mock_fn.assert_called_once_with(None, None)
    mock_db.execute.assert_not_called()
    assert result.totalSales == 87_320_000


# ---------------------------------------------------------------------------
# get_orders_by_status con use_mocks=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_orders_by_status_usa_mock_data(mock_db):
    """Con use_mocks=True debe delegar a mock_data.orders_by_status sin consultar la BD."""
    from app.schemas.responses import OrderStatusCount

    valor_mock = [OrderStatusCount(status="DELIVERED", count=198)]
    with patch(
        "app.services.analytics_service.mock_data.orders_by_status",
        return_value=valor_mock,
    ) as mock_fn:
        result = await get_orders_by_status(mock_db, use_mocks=True)

    mock_fn.assert_called_once()
    mock_db.execute.assert_not_called()
    assert result[0].status == "DELIVERED"


# ---------------------------------------------------------------------------
# get_top_products con use_mocks=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_top_products_usa_mock_data(mock_db):
    """Con use_mocks=True debe delegar a mock_data.top_products sin consultar la BD."""
    from app.schemas.responses import Pagination, TopProduct, TopProductsResponse

    valor_mock = TopProductsResponse(
        data=[TopProduct(productId="P-100", unitsSold=85, revenue=4_250_000, name=None)],
        pagination=Pagination(totalItems=1, totalPages=1, currentPage=1, pageSize=10),
    )
    with patch(
        "app.services.analytics_service.mock_data.top_products",
        return_value=valor_mock,
    ) as mock_fn:
        result = await get_top_products(mock_db, 1, 10, use_mocks=True)

    mock_fn.assert_called_once_with(1, 10)
    mock_db.execute.assert_not_called()
    assert result.data[0].productId == "P-100"


# ---------------------------------------------------------------------------
# get_average_ticket con use_mocks=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_average_ticket_usa_mock_data(mock_db):
    """Con use_mocks=True debe delegar a mock_data.average_ticket sin consultar la BD."""
    from app.schemas.responses import AverageTicketResponse

    valor_mock = AverageTicketResponse(averageTicket=79_647, currency="CLP")
    with patch(
        "app.services.analytics_service.mock_data.average_ticket",
        return_value=valor_mock,
    ) as mock_fn:
        result = await get_average_ticket(mock_db, use_mocks=True)

    mock_fn.assert_called_once()
    mock_db.execute.assert_not_called()
    assert result.averageTicket == 79_647


# ---------------------------------------------------------------------------
# get_peak_hours con use_mocks=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_peak_hours_usa_mock_data(mock_db):
    """Con use_mocks=True debe delegar a mock_data.peak_hours sin consultar la BD."""
    from app.schemas.responses import PeakHourItem

    valor_mock = [PeakHourItem(hour=18, orderCount=71)]
    with patch(
        "app.services.analytics_service.mock_data.peak_hours",
        return_value=valor_mock,
    ) as mock_fn:
        result = await get_peak_hours(mock_db, use_mocks=True)

    mock_fn.assert_called_once()
    mock_db.execute.assert_not_called()
    assert result[0].hour == 18


# ---------------------------------------------------------------------------
# get_delivery_performance con use_mocks=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_delivery_performance_usa_mock_data(mock_db):
    """Con use_mocks=True debe delegar a mock_data.delivery_performance sin consultar la BD."""
    from app.schemas.responses import DeliveryPerformanceResponse

    valor_mock = DeliveryPerformanceResponse(avgDeliveryTimeMinutes=138, totalDeliveredCount=198)
    with patch(
        "app.services.analytics_service.mock_data.delivery_performance",
        return_value=valor_mock,
    ) as mock_fn:
        result = await get_delivery_performance(mock_db, use_mocks=True)

    mock_fn.assert_called_once()
    mock_db.execute.assert_not_called()
    assert result.avgDeliveryTimeMinutes == 138
    assert result.totalDeliveredCount == 198
