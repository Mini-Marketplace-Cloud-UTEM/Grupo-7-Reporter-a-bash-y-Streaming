FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

FROM base AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM base AS runtime
COPY --from=builder /install /usr/local
COPY . .
EXPOSE 8070
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8070"]
