-- Grupo 7 — Reportería: migración 002
-- Tabla de log de quiebres de stock (evento InventoryShortage del Grupo 4).
-- Ejecutar en Supabase SQL Editor o vía psql, después de 001_initial_schema.sql.

CREATE TABLE IF NOT EXISTS inventory_shortage_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id VARCHAR NOT NULL,
  current_stock INTEGER NOT NULL,
  requested_quantity INTEGER NOT NULL,
  occurred_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_shortage_product ON inventory_shortage_log (product_id);
