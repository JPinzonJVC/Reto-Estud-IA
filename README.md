# Reto EstudIA - Plataforma de Analítica de Datos y Machine Learning 🚀

[![CI - Integración Continua (Analítica & ML)](https://github.com/JPinzonJVC/Reto-Estud-IA/actions/workflows/ci.yml/badge.svg)](https://github.com/JPinzonJVC/Reto-Estud-IA/actions/workflows/ci.yml)
[![CD - Despliegue Continuo (Analítica & ML)](https://github.com/JPinzonJVC/Reto-Estud-IA/actions/workflows/cd.yml/badge.svg)](https://github.com/JPinzonJVC/Reto-Estud-IA/actions/workflows/cd.yml)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Coverage](https://img.shields.io/badge/coverage-%3E80%25-brightgreen.svg)](https://github.com/JPinzonJVC/Reto-Estud-IA)

Plataforma modular para **análisis de datos, modelos de Machine Learning (Churn y Clustering), motor de riesgo de retención y tableros interactivos**, configurada con un pipeline de **CI/CD en GitHub Actions** adaptado para proyectos de analítica y ciencia de datos.

---

## 📋 Tabla de Contenidos
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Arquitectura de CI/CD para Analítica & ML](#-arquitectura-de-cicd-para-analítica--ml)
- [Gestión de Modelos y Datos Pesados (Git LFS)](#-gestión-de-modelos-y-datos-pesados-git-lfs)
- [Estándares de Código](#-estándares-de-código)
- [Instalación y Configuración Local](#-instalación-y-configuración-local)
- [Ejecución de Checks y Pruebas](#-ejecución-de-checks-y-pruebas)
- [Despliegue con Docker](#-despliegue-con-docker)

---

## 📂 Estructura del Proyecto

```text
Retos_StudIA/
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Pipeline CI para Analítica & ML
│       └── cd.yml                     # Pipeline CD (Build & Deploy Docker)
├── app/
│   ├── main.py                        # Entrypoint FastAPI y vistas Jinja2
│   ├── modules/
│   │   ├── retention/                 # Módulo de Retención y Fidelización
│   │   │   ├── router.py              # Endpoints REST de retención
│   │   │   ├── service.py             # Lógica y orquestación de negocio
│   │   │   └── risk_engine.py         # Motor de riesgo y recomendaciones
│   │   ├── machine_learning/          # Pipeline y Modelos de ML
│   │   │   ├── features.py            # Ingeniería de características
│   │   │   ├── preprocessing.py       # Saneamiento y normalización
│   │   │   ├── training.py            # Entrenamiento y guardado de modelos
│   │   │   ├── prediction.py          # Inferencia (Churn y Clustering)
│   │   │   └── models/                # Artefactos serializados (.pkl)
│   │   ├── analytics/                 # Módulo de Analítica y Métricas
│   │   │   └── router.py
│   │   └── affiliates/                # Módulo de Red de Afiliados
│   │       └── router.py
│   ├── templates/                     # Plantillas HTML con Jinja2
│   │   ├── dashboard/index.html
│   │   ├── retention/retention.html
│   │   ├── affiliates/affiliates.html
│   │   └── analytics/analytics.html
│   └── static/                        # Recursos estáticos
│       ├── css/style.css
│       └── js/main.js
├── scripts/
│   ├── flake8_run.py                  # Script de validación PEP 8 (90 chars)
│   └── pylint_run.py                  # Script de análisis estático con pylint-exit
├── tests/                             # Suite de pruebas unitarias
│   ├── test_features.py               # Pruebas de extracción de variables
│   ├── test_preprocessing.py          # Pruebas de transformaciones
│   ├── test_risk_engine.py            # Pruebas de motor de riesgo
│   ├── test_prediction.py             # Pruebas de inferencia ML
│   └── test_endpoints.py              # Pruebas de endpoints y servicios
├── .dockerignore
├── .flake8
├── .gitattributes                     # Configuración de Git LFS para .pkl
├── .gitignore
├── .pre-commit-config.yaml
├── .pylintrc
├── docker-compose.yml
├── Dockerfile                         # Multi-stage build optimizado para ML
├── example.env
├── pyproject.toml                     # Configuración unificada de herramientas
├── requirements.txt                   # Dependencias de producción (Pandas, Scikit-learn, FastAPI)
└── requirements-dev.txt               # Herramientas de linters, testing y seguridad
```

---

## ⚙️ Arquitectura de CI/CD para Analítica & ML

El flujo automatizado está diseñado específicamente para los retos de ciencia de datos:

```mermaid
flowchart TD
    A[Push o Pull Request] --> B[GitHub Actions: CI Pipeline]
    subgraph CI["Pipeline de CI (.github/workflows/ci.yml)"]
        B --> C[Git LFS Checkout<br/>Descarga de modelos .pkl]
        C --> D[🎨 Lint & Format<br/>Black 90ch + isort + Flake8 + Pylint]
        D --> E[🔍 Type Checking<br/>mypy app]
        D --> F[🛡️ Security Scan<br/>Bandit SAST + pip-audit]
        E --> G[🧪 Pruebas Unitarias y ML<br/>Pytest + Cobertura > 80%]
        F --> G
        D --> H[🐳 Docker Build Check<br/>Validación imagen con dependencias ML]
        G --> I[🏁 CI Status Check<br/>Gate para Branch Protection]
        H --> I
    end
    I -->|Aprobado en rama main / Tag| J[GitHub Actions: CD Pipeline]
    subgraph CD["Pipeline de CD (.github/workflows/cd.yml)"]
        J --> K[📦 Build & Push Docker<br/>Publicación en GHCR]
        K --> L[🚀 Despliegue en Entorno<br/>staging o production]
    end
```

---

## 📦 Gestión de Modelos y Datos Pesados (Git LFS)

Los artefactos binarios de modelos (`.pkl`, `.joblib`, `.parquet`) están configurados con **Git LFS** en [.gitattributes](file:///D:/Retos_StudIA/.gitattributes) para evitar que el historial de Git aumente de tamaño de forma descontrolada.

En el pipeline de CI, el paso `actions/checkout@v4` incluye `lfs: true` y una tarea de reentrenamiento fallback en caso de que se requiera regenerar los artefactos durante pruebas aisladas.

---

## 📐 Estándares de Código

- **PEP 8:** Longitud de línea estricta de 90 caracteres.
- **Docstrings:** Documentación en **Español** (Google Style: `Args`, `Returns`, `Raises`).
- **Linters:** Pylint calibrado al estándar QX IDI (puntuación objetivo: 10/10) y Flake8.
- **Tipado:** Tipado estático con `mypy` y compatibilidad con `numpy` y `pandas`.

---

## 🛠️ Instalación y Configuración Local

```bash
# 1. Clonar el repositorio con soporte Git LFS
git clone https://github.com/JPinzonJVC/Reto-Estud-IA.git
cd Reto-Estud-IA
git lfs install
git lfs pull

# 2. Crear entorno virtual
python -m venv .venv
# En Windows (PowerShell):
.venv\Scripts\Activate.ps1
# En Linux/macOS:
source .venv/bin/activate

# 3. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt

# 4. Configurar hooks de pre-commit
pre-commit install
```

---

## 🧪 Ejecución de Checks y Pruebas

```bash
# Formateo y orden de importaciones
black --check --diff app tests scripts
isort --check-only --diff app tests scripts

# Linters y calidad de código
python scripts/flake8_run.py .
python scripts/pylint_run.py .

# Chequeo estático de tipos
mypy app

# Auditoría de seguridad
bandit -r app -c pyproject.toml
pip-audit -r requirements.txt

# Pruebas unitarias y reporte de cobertura
pytest
```

---

## 🐳 Despliegue con Docker y Data Lake (MinIO)

El entorno de contenedores incluye la aplicación y la infraestructura del **Data Lake** basada en **MinIO** (S3 compatible):

- **App:** `http://localhost:8000` (Dashboard interactivo y API FastAPI).
- **MinIO S3 API:** `http://localhost:9000` (Ingesta, lectura y escritura de datasets con `boto3`).
- **MinIO Console UI:** `http://localhost:9001` (Consola web de administración del Data Lake).
- **Credenciales por defecto:** Usuario `minioadmin` | Contraseña `minioadmin123`.

### Buckets auto-aprovisionados al iniciar:
1. `datalake-raw`: Almacenamiento de datasets crudos y fuentes externas sin procesar.
2. `datalake-processed`: Tablas limpias, transformadas y datasets de características (features).
3. `datalake-models`: Serialización y versionado de modelos ML entrenados (`.pkl`, `.joblib`).

### Levantar el entorno completo:
```bash
docker-compose up --build
```
