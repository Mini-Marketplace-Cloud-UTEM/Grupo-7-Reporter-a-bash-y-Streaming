-- Grupo 7 — Reportería: schema inicial
-- Ejecutar en Supabase SQL Editor o vía psql

CREATE TABLE IF NOT EXISTS fact_sales_summary (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  period_date TIMESTAMP NOT NULL,
  total_sales_amount NUMERIC NOT NULL DEFAULT 0,
  total_orders_count INTEGER NOT NULL DEFAULT 0,
  aggregation_type VARCHAR(20) NOT NULL CHECK (aggregation_type IN ('REAL_TIME', 'BATCH_RECALCULATED')),
  updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_period ON fact_sales_summary (period_date);

CREATE TABLE IF NOT EXISTS agg_top_products (
  product_id VARCHAR PRIMARY KEY,
  total_units_sold INTEGER NOT NULL DEFAULT 0,
  total_revenue_generated NUMERIC NOT NULL DEFAULT 0,
  last_calculated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agg_top_products_units ON agg_top_products (total_units_sold DESC);

-- Tabla auxiliar para conteo de estados de pedido (poblada por el worker)
CREATE TABLE IF NOT EXISTS order_status_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id VARCHAR NOT NULL,
  status VARCHAR(50) NOT NULL,
  occurred_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_order_status_log_status ON order_status_log (status);

-- Tabla auxiliar para métricas de despacho (poblada por ShipmentDelivered)
CREATE TABLE IF NOT EXISTS shipment_delivery_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  shipment_id VARCHAR NOT NULL UNIQUE,
  order_id VARCHAR NOT NULL,
  delivered_at TIMESTAMP NOT NULL,
  city VARCHAR(100),
  delivery_time_minutes INTEGER,
  recorded_at TIMESTAMP NOT NULL DEFAULT now()
);
