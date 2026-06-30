"""
Pruebas unitarias para app/services/analytics_service.py.

Verifica la lógica de cada función analítica usando mocks de AsyncSession
para aislar las pruebas de la base de datos real.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.analytics_service import (
    get_average_ticket,
    get_delivery_performance,
    get_orders_by_status,
    get_peak_hours,
    get_sales_report,
    get_top_products,
    log_order_status,
    log_shipment_delivery,
    upsert_sales_from_order,
    upsert_top_product,
)

# ---------------------------------------------------------------------------
# get_sales_report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sales_report_sin_fechas():
    """Sin filtros de fecha debe retornar la suma total de ventas y pedidos."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.one.return_value = (100000, 5)
    mock_db.execute.return_value = mock_result

    report = await get_sales_report(mock_db, None, None)

    assert report.totalSales == 100000
    assert report.totalOrders == 5
    assert report.currency == "CLP"
    assert report.period.from_ is None
    assert report.period.to is None


@pytest.mark.asyncio
async def test_get_sales_report_con_fechas():
    """Con rango de fechas debe incluirlas en el período de la respuesta."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.one.return_value = (49990, 1)
    mock_db.execute.return_value = mock_result

    from_date = date(2024, 1, 1)
    to_date = date(2024, 1, 31)
    report = await get_sales_report(mock_db, from_date, to_date)

    assert report.totalSales == 49990
    assert report.totalOrders == 1
    assert report.period.from_ == "2024-01-01"
    assert report.period.to == "2024-01-31"


@pytest.mark.asyncio
async def test_get_sales_report_resultado_nulo():
    """Cuando la BD no tiene datos (NULL) debe retornar ceros en lugar de error."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.one.return_value = (None, None)
    mock_db.execute.return_value = mock_result

    report = await get_sales_report(mock_db, None, None)

    assert report.totalSales == 0
    assert report.totalOrders == 0


# ---------------------------------------------------------------------------
# get_orders_by_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_orders_by_status_con_datos():
    """Debe retornar la lista de estados con sus conteos correctos."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        ("PENDING", 3),
        ("CONFIRMED", 7),
        ("DELIVERED", 15),
    ]
    mock_db.execute.return_value = mock_result

    result = await get_orders_by_status(mock_db)

    assert len(result) == 3
    assert result[0].status == "PENDING"
    assert result[0].count == 3
    assert result[2].status == "DELIVERED"
    assert result[2].count == 15


@pytest.mark.asyncio
async def test_get_orders_by_status_vacio():
    """Cuando no existen registros en order_status_log debe retornar lista vacía."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    result = await get_orders_by_status(mock_db)

    assert result == []


# ---------------------------------------------------------------------------
# get_top_products
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_top_products_paginado():
    """Debe retornar los productos con su paginación cuando existen registros."""
    mock_db = AsyncMock()

    # Primera llamada: count total
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 10

    # Segunda llamada: lista de productos
    producto = MagicMock()
    producto.product_id = "P-100"
    producto.total_units_sold = 50
    producto.total_revenue_generated = Decimal("250000")

    mock_list_result = MagicMock()
    mock_list_result.scalars.return_value.all.return_value = [producto]

    mock_db.execute.side_effect = [mock_count_result, mock_list_result]

    response = await get_top_products(mock_db, page=1, page_size=5)

    assert response.pagination.totalItems == 10
    assert response.pagination.totalPages == 2
    assert response.pagination.currentPage == 1
    assert len(response.data) == 1
    assert response.data[0].productId == "P-100"
    assert response.data[0].unitsSold == 50
    assert response.data[0].revenue == 250000


@pytest.mark.asyncio
async def test_get_top_products_lista_vacia():
    """Con colección vacía debe retornar al menos 1 página (techo entero)."""
    mock_db = AsyncMock()

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 0

    mock_list_result = MagicMock()
    mock_list_result.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [mock_count_result, mock_list_result]

    response = await get_top_products(mock_db, page=1, page_size=10)

    assert response.pagination.totalItems == 0
    assert response.pagination.totalPages == 1
    assert response.data == []


# ---------------------------------------------------------------------------
# get_average_ticket
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_average_ticket_normal():
    """Con ventas y pedidos debe calcular el promedio correctamente."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.one.return_value = (Decimal("99980"), 2)
    mock_db.execute.return_value = mock_result

    response = await get_average_ticket(mock_db)

    assert response.averageTicket == 49990


@pytest.mark.asyncio
async def test_get_average_ticket_sin_ordenes():
    """Sin pedidos (valores NULL) debe retornar ticket promedio igual a 0."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.one.return_value = (None, None)
    mock_db.execute.return_value = mock_result

    response = await get_average_ticket(mock_db)

    # total_orders = int(None or 1) = 1, total_sales = 0 → avg = 0
    assert response.averageTicket == 0


# ---------------------------------------------------------------------------
# get_peak_hours
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_peak_hours_con_datos():
    """Debe retornar la lista de horas pico con sus conteos de pedidos."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        (10, 5),
        (14, 12),
        (18, 20),
    ]
    mock_db.execute.return_value = mock_result

    result = await get_peak_hours(mock_db)

    assert len(result) == 3
    assert result[0].hour == 10
    assert result[0].orderCount == 5
    assert result[2].hour == 18
    assert result[2].orderCount == 20


@pytest.mark.asyncio
async def test_get_peak_hours_sin_datos():
    """Sin registros en fact_sales_summary debe retornar lista vacía."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db.execute.return_value = mock_result

    result = await get_peak_hours(mock_db)

    assert result == []


# ---------------------------------------------------------------------------
# get_delivery_performance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_delivery_performance_con_datos():
    """Debe retornar tiempo promedio y total de envíos cuando existen registros."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (45, 120)
    mock_db.execute.return_value = mock_result

    response = await get_delivery_performance(mock_db)

    assert response.avgDeliveryTimeMinutes == 45
    assert response.totalDeliveredCount == 120


@pytest.mark.asyncio
async def test_get_delivery_performance_sin_datos():
    """Sin entregas registradas debe retornar ceros en ambas métricas."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = (None, 0)
    mock_db.execute.return_value = mock_result

    response = await get_delivery_performance(mock_db)

    assert response.avgDeliveryTimeMinutes == 0
    assert response.totalDeliveredCount == 0


@pytest.mark.asyncio
async def test_get_delivery_performance_row_none():
    """Cuando fetchone retorna None debe retornar ceros sin error."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_db.execute.return_value = mock_result

    response = await get_delivery_performance(mock_db)

    assert response.avgDeliveryTimeMinutes == 0
    assert response.totalDeliveredCount == 0


# ---------------------------------------------------------------------------
# upsert_sales_from_order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_sales_registro_nuevo():
    """Sin registro previo del día debe crear uno nuevo en la BD."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    period_date = datetime(2024, 6, 15, 10, 0, 0)
    amount = Decimal("49990")
    correlation_id = str(uuid.uuid4())

    await upsert_sales_from_order(mock_db, period_date, amount, correlation_id)

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_sales_registro_existente():
    """Con registro previo del día debe incrementar ventas y pedidos."""
    mock_db = AsyncMock()

    registro_existente = MagicMock()
    registro_existente.total_sales_amount = Decimal("50000")
    registro_existente.total_orders_count = 1
    registro_existente.aggregation_type = "REAL_TIME"
    registro_existente.updated_at = datetime.now(UTC)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = registro_existente
    mock_db.execute.return_value = mock_result

    period_date = datetime(2024, 6, 15, 15, 0, 0)
    amount = Decimal("29990")

    await upsert_sales_from_order(mock_db, period_date, amount, "corr-123")

    assert registro_existente.total_sales_amount == Decimal("79990")
    assert registro_existente.total_orders_count == 2
    assert registro_existente.aggregation_type == "REAL_TIME"
    mock_db.add.assert_not_called()
    mock_db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# upsert_top_product
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_top_product_registro_nuevo():
    """Sin registro previo para el producto debe crear uno nuevo."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    await upsert_top_product(mock_db, "P-100", 5, Decimal("49990"))

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_top_product_registro_existente():
    """Con registro previo debe acumular unidades e ingresos."""
    mock_db = AsyncMock()

    registro_existente = MagicMock()
    registro_existente.total_units_sold = 10
    registro_existente.total_revenue_generated = Decimal("100000")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = registro_existente
    mock_db.execute.return_value = mock_result

    await upsert_top_product(mock_db, "P-100", 3, Decimal("30000"))

    assert registro_existente.total_units_sold == 13
    assert registro_existente.total_revenue_generated == Decimal("130000")
    mock_db.add.assert_not_called()
    mock_db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# log_order_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_order_status_inserta_registro():
    """Debe añadir un OrderStatusLog a la sesión y hacer commit."""
    mock_db = AsyncMock()
    occurred_at = datetime(2024, 6, 15, 10, 0, 0)

    await log_order_status(mock_db, order_id="ORD-001", status="CREATED", occurred_at=occurred_at)

    mock_db.add.assert_called_once()
    added_obj = mock_db.add.call_args.args[0]
    assert added_obj.order_id == "ORD-001"
    assert added_obj.status == "CREATED"
    assert added_obj.occurred_at == occurred_at
    mock_db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# log_shipment_delivery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_shipment_delivery_inserta_nuevo_registro():
    """Sin registro previo para el shipment_id debe insertar y hacer commit."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    delivered_at = datetime(2024, 6, 15, 14, 30, 0)

    await log_shipment_delivery(
        mock_db,
        shipment_id="SHP-001",
        order_id="ORD-001",
        delivered_at=delivered_at,
        city="Santiago",
        delivery_time_minutes=45,
    )

    mock_db.add.assert_called_once()
    added_obj = mock_db.add.call_args.args[0]
    assert added_obj.shipment_id == "SHP-001"
    assert added_obj.order_id == "ORD-001"
    assert added_obj.delivered_at == delivered_at
    assert added_obj.city == "Santiago"
    assert added_obj.delivery_time_minutes == 45
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_log_shipment_delivery_no_duplica_registro_existente():
    """Si ya existe un registro para el shipment_id no debe insertar ni hacer commit."""
    mock_db = AsyncMock()
    registro_existente = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = registro_existente
    mock_db.execute.return_value = mock_result

    delivered_at = datetime(2024, 6, 15, 14, 30, 0)

    await log_shipment_delivery(
        mock_db,
        shipment_id="SHP-001",
        order_id="ORD-001",
        delivered_at=delivered_at,
        city="Valparaíso",
        delivery_time_minutes=None,
    )

    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_log_shipment_delivery_acepta_campos_opcionales_nulos():
    """Debe funcionar correctamente cuando city y delivery_time_minutes son None."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    await log_shipment_delivery(
        mock_db,
        shipment_id="SHP-002",
        order_id="ORD-002",
        delivered_at=datetime(2024, 6, 16, 9, 0, 0),
        city=None,
        delivery_time_minutes=None,
    )

    mock_db.add.assert_called_once()
    added_obj = mock_db.add.call_args.args[0]
    assert added_obj.city is None
    assert added_obj.delivery_time_minutes is None
    mock_db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# log_order_status — comportamiento de log puro (no upsert)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_order_status_es_log_puro_no_upsert():
    """
    log_order_status debe crear un nuevo registro en cada llamada.

    A diferencia de log_shipment_delivery (upsert por shipment_id),
    esta función no comprueba si ya existe una entrada para el mismo
    order_id: simplemente inserta. Así el conteo en get_orders_by_status
    refleja cada transición de estado, no solo la última.
    """
    mock_db = AsyncMock()
    occurred_at = datetime(2024, 6, 15, 10, 0, 0)

    await log_order_status(mock_db, order_id="ORD-001", status="CREATED", occurred_at=occurred_at)
    await log_order_status(mock_db, order_id="ORD-001", status="CONFIRMED", occurred_at=occurred_at)

    # Dos llamadas = dos add(), uno por cada cambio de estado
    assert mock_db.add.call_count == 2
    assert mock_db.commit.await_count == 2
    # La función no ejecuta ningún SELECT previo (no es upsert)
    mock_db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# get_orders_by_status — un único estado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_orders_by_status_un_unico_estado():
    """Con solo un estado registrado debe retornar una lista con un único elemento."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("CREATED", 1)]
    mock_db.execute.return_value = mock_result

    result = await get_orders_by_status(mock_db)

    assert len(result) == 1
    assert result[0].status == "CREATED"
    assert result[0].count == 1


# ---------------------------------------------------------------------------
# get_peak_hours — hora 0 (medianoche)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_peak_hours_incluye_hora_cero():
    """
    La hora 0 (medianoche) debe ser manejada correctamente.

    func.extract devuelve un float (0.0); int(0.0) debe ser 0 sin error.
    """
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [(0.0, 3), (14.0, 8)]
    mock_db.execute.return_value = mock_result

    result = await get_peak_hours(mock_db)

    assert result[0].hour == 0
    assert result[0].orderCount == 3
    assert result[1].hour == 14
