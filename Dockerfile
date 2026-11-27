# =============================================================
# Etapa 1: Compilación de la interfaz React
# =============================================================
FROM node:22-alpine AS frontend-builder

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN npm ci --prefix frontend
COPY frontend ./frontend
RUN npm --prefix frontend run build

# =============================================================
# Etapa 2: Builder (Compilación e instalación de dependencias ML)
# =============================================================
FROM python:3.10-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================
# Etapa 3: Runtime (Entorno de producción ligero y seguro)
# =============================================================
FROM python:3.10-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Crear usuario y grupo sin privilegios para ejecución segura
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m appuser

# Copiar dependencias de Python desde la etapa builder
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copiar código fuente, templates, estáticos y módulos
COPY --chown=appuser:appgroup . /app

# Incorporar el bundle React generado sin incluir Node.js en el runtime.
COPY --from=frontend-builder --chown=appuser:appgroup /build/app/static/react /app/app/static/react

# Asegurar directorios de entrada de datos, artefactos ML y logs con permisos adecuados
RUN mkdir -p /app/input /app/logs /var/lib/actho/ml_artifacts && \
    chown -R appuser:appgroup /app/input /app/logs /var/lib/actho

USER appuser

EXPOSE 8000

# Verificación de salud del contenedor
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
