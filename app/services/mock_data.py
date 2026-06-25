"""
Datos mock para todos los endpoints de reportería.

Activos únicamente cuando USE_MOCKS=true. Reflejan el mismo dataset que las
respuestas de ejemplo precargadas en la colección Insomnia del proyecto.
"""

from datetime import date

from app.schemas.responses import (
    AverageTicketResponse,
    DeliveryPerformanceResponse,
    OrderStatusCount,
    Pagination,
    PeakHourItem,
    SalesPeriod,
    SalesReport,
    TopProduct,
    TopProductsResponse,
)

_TOP_PRODUCTS_ALL: list[TopProduct] = [
    TopProduct(productId="P-100", name="Notebook Lenovo IdeaPad", unitsSold=85, revenue=4_250_000),
    TopProduct(productId="P-042", name="Mouse Inalámbrico Logitech", unitsSold=74, revenue=888_000),
    TopProduct(
        productId="P-207", name="Audífonos Sony WH-1000XM5", unitsSold=61, revenue=3_050_000
    ),
    TopProduct(
        productId="P-318", name="Teclado Mecánico Redragon", unitsSold=58, revenue=1_160_000
    ),
    TopProduct(
        productId="P-055", name="Monitor Samsung 27 pulgadas", unitsSold=52, revenue=5_200_000
    ),
    TopProduct(productId="P-411", name="Silla Gamer DXRacer", unitsSold=49, revenue=4_900_000),
    TopProduct(productId="P-123", name="Webcam Logitech C920", unitsSold=43, revenue=860_000),
    TopProduct(productId="P-299", name="Disco SSD Samsung 1TB", unitsSold=38, revenue=1_520_000),
    TopProduct(
        productId="P-077", name="Parlante Bluetooth JBL Flip 6", unitsSold=35, revenue=700_000
    ),
    TopProduct(productId="P-501", name="Hub USB-C 7 en 1 Anker", unitsSold=29, revenue=580_000),
    TopProduct(
        productId="P-088", name="Impresora HP LaserJet Pro", unitsSold=24, revenue=2_400_000
    ),
    TopProduct(productId="P-334", name="Cámara GoPro Hero 12", unitsSold=21, revenue=2_100_000),
    TopProduct(productId="P-612", name="Router TP-Link Wi-Fi 6", unitsSold=19, revenue=760_000),
    TopProduct(
        productId="P-145", name="Tablet Samsung Galaxy Tab S9", unitsSold=16, revenue=3_200_000
    ),
    TopProduct(productId="P-720", name="Control PS5 DualSense", unitsSold=14, revenue=560_000),
    TopProduct(productId="P-831", name="Cargador GaN 65W Baseus", unitsSold=12, revenue=240_000),
    TopProduct(productId="P-903", name="Smart TV LG 55 OLED", unitsSold=10, revenue=7_500_000),
    TopProduct(productId="P-219", name="Micrófono Blue Yeti", unitsSold=8, revenue=480_000),
    TopProduct(productId="P-467", name="Soporte Monitor Ergotron", unitsSold=6, revenue=360_000),
    TopProduct(productId="P-558", name="Cable HDMI 2.1 4K 2m", unitsSold=5, revenue=50_000),
    TopProduct(productId="P-661", name="Mousepad XL Gaming", unitsSold=4, revenue=60_000),
    TopProduct(
        productId="P-774", name="Adaptador USB-C a DisplayPort", unitsSold=3, revenue=45_000
    ),
    TopProduct(productId="P-882", name="Funda Laptop 15 pulgadas", unitsSold=2, revenue=30_000),
    TopProduct(
        productId="P-991", name="Limpiador Pantallas Kensington", unitsSold=2, revenue=20_000
    ),
    TopProduct(productId="P-002", name="Lámpara LED USB Escritorio", unitsSold=1, revenue=15_000),
]


def sales_report(from_date: date | None, to_date: date | None) -> SalesReport:
    if from_date or to_date:
        return SalesReport(
            period=SalesPeriod(
                **{
                    "from": str(from_date) if from_date else None,
                    "to": str(to_date) if to_date else None,
                }
            ),
            totalSales=24_850_000,
            totalOrders=312,
            currency="CLP",
        )
    return SalesReport(
        period=SalesPeriod(**{"from": None, "to": None}),
        totalSales=87_320_000,
        totalOrders=1_148,
        currency="CLP",
    )


def orders_by_status() -> list[OrderStatusCount]:
    return [
        OrderStatusCount(status="DELIVERED", count=198),
        OrderStatusCount(status="CONFIRMED", count=67),
        OrderStatusCount(status="PENDING", count=31),
        OrderStatusCount(status="CANCELLED", count=12),
        OrderStatusCount(status="SHIPPED", count=4),
    ]


def top_products(page: int, page_size: int) -> TopProductsResponse:
    total = len(_TOP_PRODUCTS_ALL)
    total_pages = max(1, -(-total // page_size))
    start = (page - 1) * page_size
    slice_ = _TOP_PRODUCTS_ALL[start : start + page_size]
    return TopProductsResponse(
        data=slice_,
        pagination=Pagination(
            totalItems=total,
            totalPages=total_pages,
            currentPage=page,
            pageSize=page_size,
        ),
    )


def average_ticket() -> AverageTicketResponse:
    return AverageTicketResponse(averageTicket=79_647, currency="CLP")


def peak_hours() -> list[PeakHourItem]:
    counts = [
        4,
        2,
        1,
        0,
        0,
        1,
        3,
        8,
        14,
        21,
        27,
        35,
        48,
        52,
        44,
        38,
        31,
        29,
        63,
        71,
        58,
        41,
        22,
        11,
    ]
    return [PeakHourItem(hour=h, orderCount=c) for h, c in enumerate(counts)]


def delivery_performance() -> DeliveryPerformanceResponse:
    return DeliveryPerformanceResponse(avgDeliveryTimeMinutes=138, totalDeliveredCount=198)
