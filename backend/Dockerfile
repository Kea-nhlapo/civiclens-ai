# Stage 1: convert the crack and streetlight models to ONNX. This needs PyTorch,
# which is large, so it stays in this stage and never reaches the final image.
FROM python:3.12-slim AS models
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CIVICLENS_MODEL_DIR=/models
WORKDIR /build
COPY requirements-export.txt .
RUN pip install --no-cache-dir -r requirements-export.txt
COPY app/__init__.py app/__init__.py
COPY app/detection app/detection
COPY tools tools
RUN python -m tools.export_models && python -m app.detection.model_store

# Stage 2: the app, with only ONNX Runtime and the three model files.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 CIVICLENS_MODEL_DIR=/app/models
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY --from=models /models ./models
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
