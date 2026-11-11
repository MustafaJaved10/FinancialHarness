FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS sandbox
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY brain_live.py ./
COPY stock_assistant/ stock_assistant/
RUN mkdir -p /sandbox-ipc && touch /sandbox-ipc/.keep && chown -R 10001:10001 /sandbox-ipc
USER 10001:10001
CMD ["python", "-m", "stock_assistant.analysis_worker"]

FROM sandbox AS app
USER root
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY data/ data/
COPY tests/ tests/
COPY --from=frontend /src/dist/ frontend/dist/
RUN mkdir -p /app/results && chown 10001:10001 /app/results
USER 10001:10001
CMD ["uvicorn", "stock_assistant.api:app", "--host", "0.0.0.0", "--port", "8000"]
