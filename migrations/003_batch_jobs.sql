-- Tabla de control de idempotencia para el proceso batch de recálculo.
-- Cada clave de idempotencia queda registrada con su job_id y estado
-- para evitar ejecuciones duplicadas ante reintentos del cliente.
CREATE TABLE IF NOT EXISTS batch_jobs (
  idempotency_key UUID PRIMARY KEY,
  job_id          UUID         NOT NULL,
  status          VARCHAR(20)  NOT NULL DEFAULT 'QUEUED',
  created_at      TIMESTAMP    NOT NULL DEFAULT now(),
  completed_at    TIMESTAMP
);
