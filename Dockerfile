FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

# Cloud Run inyecta PORT en tiempo de ejecución (por defecto 8080); forma
# shell para que ${PORT} se expanda, no forma exec.
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8080}
