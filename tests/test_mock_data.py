"""
Pruebas unitarias para app/services/mock_data.py.

Verifica que las funciones puras de datos mock retornen los valores
esperados sin depender de base de datos ni servicios externos.
"""

import math
from datetime import date

import pytest

from app.services.mock_data import (
    average_ticket,
    delivery_performance,
    orders_by_status,
    peak_hours,
    sales_report,
    top_products,
)


# ---------------------------------------------------------------------------
# sales_report
# ---------------------------------------------------------------------------


def test_sales_report_sin_fechas():
    """Sin fechas debe retornar el consolidado histórico completo."""
    result = sales_report(None, None)
    assert result.totalSales == 87_320_000
    assert result.totalOrders == 1_148
    assert result.currency == "CLP"
    assert result.period.from_ is None


def test_sales_report_con_fechas():
    """Con fechas definidas debe retornar el dataset filtrado del período."""
    result = sales_report(date(2024, 1, 1), date(2024, 1, 31))
    assert result.totalSales == 24_850_000
    assert result.totalOrders == 312
    assert result.period.from_ == "2024-01-01"


# ---------------------------------------------------------------------------
# orders_by_status
# ---------------------------------------------------------------------------


def test_orders_by_status_retorna_cinco_elementos():
    """Debe retornar exactamente 5 estados de pedido."""
    result = orders_by_status()
    assert len(result) == 5


def test_orders_by_status_primer_elemento_delivered():
    """El primer estado de la lista debe ser DELIVERED."""
    result = orders_by_status()
    assert result[0].status == "DELIVERED"


# ---------------------------------------------------------------------------
# top_products
# ---------------------------------------------------------------------------


def test_top_products_pagina_1_page_size_10():
    """Página 1 con tamaño 10 debe retornar 10 productos y paginación correcta."""
    result = top_products(1, 10)
    assert len(result.data) == 10
    assert result.pagination.currentPage == 1
    assert result.pagination.pageSize == 10


def test_top_products_pagina_2_page_size_10():
    """Página 2 con tamaño 10 debe retornar los siguientes 10 productos."""
    result = top_products(2, 10)
    result_p1 = top_products(1, 10)
    # Las IDs de productos de p2 no deben coincidir con las de p1
    ids_p1 = {p.productId for p in result_p1.data}
    ids_p2 = {p.productId for p in result.data}
    assert ids_p1.isdisjoint(ids_p2)


def test_top_products_page_size_mayor_total():
    """Con pageSize igual al total de productos debe retornar todos en una sola página."""
    result = top_products(1, 100)
    assert len(result.data) == 25
    assert result.pagination.totalPages == 1


def test_top_products_total_pages_calculado_correctamente():
    """Con 25 productos y pageSize=5 deben haber 5 páginas en total."""
    result = top_products(1, 5)
    assert result.pagination.totalPages == math.ceil(25 / 5)


# ---------------------------------------------------------------------------
# average_ticket
# ---------------------------------------------------------------------------


def test_average_ticket_valor_correcto():
    """El ticket promedio debe ser 79647 CLP."""
    result = average_ticket()
    assert result.averageTicket == 79_647


# ---------------------------------------------------------------------------
# peak_hours
# ---------------------------------------------------------------------------


def test_peak_hours_retorna_24_elementos():
    """Debe retornar exactamente 24 franjas horarias (0-23)."""
    result = peak_hours()
    assert len(result) == 24


def test_peak_hours_hora_cero_tiene_cuatro_pedidos():
    """La hora 0 (medianoche) debe tener un conteo de 4 pedidos."""
    result = peak_hours()
    hora_cero = next(item for item in result if item.hour == 0)
    assert hora_cero.orderCount == 4


# ---------------------------------------------------------------------------
# delivery_performance
# ---------------------------------------------------------------------------


def test_delivery_performance_valores_correctos():
    """El tiempo promedio debe ser 138 minutos y el total de entregas 198."""
    result = delivery_performance()
    assert result.avgDeliveryTimeMinutes == 138
    assert result.totalDeliveredCount == 198
