# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN --mount=type=secret,id=proxy_ca NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./backend/requirements.txt
# CPU XGBoost avoids downloading the unused NVIDIA runtime.
RUN --mount=type=secret,id=proxy_ca if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ ./backend/
COPY --from=frontend /app/frontend/dist ./frontend/dist
RUN useradd --create-home appuser && mkdir -p backend/data backend/models /tmp/matplotlib && chown -R appuser:appuser /app
USER appuser
ENV PYTHONPATH=/app/backend MPLCONFIGDIR=/tmp/matplotlib
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
