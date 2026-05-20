# Stage 1: builder
FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# Stage 2: runtime
FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY productboard_sync/ ./productboard_sync/

RUN useradd --no-create-home --shell /bin/false appuser &&     chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["python", "-m", "productboard_sync"]
CMD ["--entity", "all"]
