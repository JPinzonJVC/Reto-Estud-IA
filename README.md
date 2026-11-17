# Reto EstudIA - Plataforma de Analítica de Datos y Machine Learning 🚀

[![CI - Integración Continua (Analítica & ML)](https://github.com/JPinzonJVC/Reto-Estud-IA/actions/workflows/ci.yml/badge.svg)](https://github.com/JPinzonJVC/Reto-Estud-IA/actions/workflows/ci.yml)
[![CD - Despliegue Continuo (Analítica & ML)](https://github.com/JPinzonJVC/Reto-Estud-IA/actions/workflows/cd.yml/badge.svg)](https://github.com/JPinzonJVC/Reto-Estud-IA/actions/workflows/cd.yml)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![Coverage](https://img.shields.io/badge/coverage-%3E80%25-brightgreen.svg)](https://github.com/JPinzonJVC/Reto-Estud-IA)

Plataforma modular para **análisis de datos, modelos de Machine Learning (Churn y Clustering), motor de riesgo de retención, base de datos relacional PostgreSQL y tableros interactivos**, configurada con un pipeline de **CI/CD en GitHub Actions** adaptado para proyectos de analítica y ciencia de datos.

---

## 📋 Tabla de Contenidos
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Arquitectura de CI/CD para Analítica & ML](#-arquitectura-de-cicd-para-analítica--ml)
- [Gestión de Insumos y Datos Locales (Carpeta input)](#-gestión-de-insumos-y-datos-locales-carpeta-input)
- [Exclusión de Modelos y Datos del Repositorio](#-exclusión-de-modelos-y-datos-del-repositorio)
- [Estándares de Código](#-estándares-de-código)
- [Instalación y Configuración Local](#-instalación-y-configuración-local)
- [Ejecución de Checks y Pruebas](#-ejecución-de-checks-y-pruebas)
- [Despliegue con Docker y PostgreSQL](#-despliegue-con-docker-y-postgresql)

---

## 📂 Estructura del Proyecto

```text
Retos_StudIA/
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Pipeline CI para Analítica & ML
│       └── cd.yml                     # Pipeline CD (Build & Deploy Docker)
├── app/
│   ├── database.py                    # Conexión, motor y sesiones PostgreSQL (SQLAlchemy)
│   ├── main.py                        # Entrypoint FastAPI y vistas Jinja2
│   ├── modules/
│   │   ├── eda/                           # Pipeline ETL Medallion (Bronze -> Silver -> Gold -> Audit)
│   │   │   ├── config.py                  # Configuración portable hacia input/
│   │   │   ├── etl_config.json            # Parámetros de negocio y rutas Medallion
│   │   │   ├── bronze.py                  # Ingesta y verificación SHA-256
│   │   │   ├── scd2.py                    # Reconstrucción histórica SCD Tipo 2
│   │   │   ├── silver.py                  # Modelo dimensional puro (Dimensiones y Hechos)
│   │   │   ├── gold.py                    # Agregaciones analíticas y semáforo heurístico
│   │   │   ├── audit.py                   # Bitácoras de calidad, duplicados y reconciliación
│   │   │   └── pipeline.py                # Orquestador ejecutable del pipeline Medallion
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
├── input/                             # Capas Medallion y datos locales (.csv, .parquet) [NO sube a Git]
│   ├── bronze/                        # Copia inmutable verificada con SHA-256 (.csv)
│   ├── silver/                        # Dimensiones (+SCD2) y Hechos depurados (.csv y .parquet)
│   ├── gold/                          # Agregaciones analíticas de negocio (.csv y .parquet)
│   ├── audit/                         # Hashes, duplicados, calidad y reconciliación (.csv y .parquet)
│   ├── normalizados/                  # Tablas normalizadas de entrada al ETL
│   ├── CSV/                           # 47 archivos CSV crudos originales
│   └── .gitkeep
├── notebooks/                         # Notebooks de EDA y Refactorización Dimensional
│   ├── analisis_exploratorio.ipynb
│   ├── resultados_esperados_actho.ipynb
│   └── refactorizacion_modelo_dimensional.ipynb
├── docs/                              # Documentación técnica del EDA y Modelo Medallion
│   ├── README_EDA_MEDALLION_ACTHO360.md
│   └── DOCUMENTACION_MODELO_REFACTORIZADO.md
├── scripts/
│   ├── flake8_run.py                  # Script de validación PEP 8 (90 chars)
│   └── pylint_run.py                  # Script de análisis estático con pylint-exit
├── tests/                             # Suite de pruebas unitarias
│   ├── test_database.py               # Pruebas de configuración y conexión a base de datos
│   ├── test_features.py               # Pruebas de extracción de variables
│   ├── test_preprocessing.py          # Pruebas de transformaciones
│   ├── test_risk_engine.py            # Pruebas de motor de riesgo
│   ├── test_prediction.py             # Pruebas de inferencia ML
│   └── test_endpoints.py              # Pruebas de endpoints y servicios
├── .dockerignore
├── .flake8
├── .gitignore                         # Exclusiones de Git (ignora input/*, models/*, .csv, .pkl)
├── .pre-commit-config.yaml
├── .pylintrc
├── docker-compose.yml                 # Orquestación con App y PostgreSQL
├── Dockerfile                         # Multi-stage build optimizado para ML
├── example.env                        # Variables de entorno de ejemplo con PostgreSQL
├── pyproject.toml                     # Configuración unificada de herramientas
├── requirements.txt                   # Dependencias (Pandas, Scikit-learn, SQLAlchemy, etc.)
└── requirements-dev.txt               # Herramientas de linters, testing y seguridad
```

---

## 📥 Gestión de Insumos y Datos Locales (Carpeta input)

La carpeta [input/](file:///D:/Retos_StudIA/input/) está destinada al almacenamiento local de fuentes de datos crudas y procesadas (`.csv`, `.parquet`, `.xlsx`):

* **Privacidad y Exclusión de Git:** Todos los archivos dentro de `input/` están explícitamente excluidos del repositorio mediante [.gitignore](file:///D:/Retos_StudIA/.gitignore) y [.dockerignore](file:///D:/Retos_StudIA/.dockerignore), conservando únicamente el archivo `input/.gitkeep`.
* **Montaje en Docker:** En `docker-compose.yml`, el directorio `./input` se monta como volumen en `/app/input`, permitiendo a los pipelines de datos acceder a los archivos locales directamente en el contenedor sin incluirlos en la imagen construida.

---

## ⚙️ Arquitectura de CI/CD para Analítica & ML

El flujo automatizado está diseñado específicamente para los retos de ciencia de datos:

```mermaid
flowchart TD
    A[Push o Pull Request] --> B[GitHub Actions: CI Pipeline]
    subgraph CI["Pipeline de CI (.github/workflows/ci.yml)"]
        B --> C[🎨 Lint & Format<br/>Black 90ch + isort + Flake8 + Pylint]
        C --> D[🔍 Type Checking<br/>mypy app]
        C --> E[🛡️ Security Scan<br/>Bandit SAST + pip-audit]
        D --> F[🧪 Pruebas Unitarias y ML<br/>Pytest + Cobertura > 80%]
        E --> F
        C --> G[🐳 Docker Build Check<br/>Validación imagen con dependencias ML]
        F --> H[🏁 CI Status Check<br/>Gate para Branch Protection]
        G --> H
    end
    I -->|Aprobado en rama main / Tag| J[GitHub Actions: CD Pipeline]
    subgraph CD["Pipeline de CD (.github/workflows/cd.yml)"]
        J --> K[📦 Build & Push Docker<br/>Publicación en GHCR]
        K --> L[🚀 Despliegue en Entorno<br/>staging o production]
    end
```

---

## 🔒 Exclusión de Modelos y Datos del Repositorio

Tanto los insumos de datos (`.csv`, `.parquet`, `.xlsx`) como los artefactos binarios de modelos de Machine Learning (`.pkl`, `.joblib`, `.h5`, `.pt`, etc.) están **estrictamente excluidos del repositorio de Git** mediante [.gitignore](file:///D:/Retos_StudIA/.gitignore) y [.dockerignore](file:///D:/Retos_StudIA/.dockerignore).

* **Generación en CI:** En el pipeline de GitHub Actions, los modelos de prueba se entrenan y generan de forma autónoma al momento de la ejecución (`python -m app.modules.machine_learning.training`).
* **Persistencia Local:** Los modelos entrenados localmente se guardan en `app/modules/machine_learning/models/`, conservando únicamente el archivo marcador `.gitkeep` en control de versiones.

---

## 📐 Estándares de Código

- **PEP 8:** Longitud de línea estricta de 90 caracteres.
- **Docstrings:** Documentación en **Español** (Google Style: `Args`, `Returns`, `Raises`).
- **Linters:** Pylint calibrado al estándar QX IDI (puntuación objetivo: 10/10) y Flake8.
- **Tipado:** Tipado estático con `mypy` y compatibilidad con `numpy` y `pandas`.

---

## 🛠️ Instalación y Configuración Local

```bash
# 1. Clonar el repositorio
git clone https://github.com/JPinzonJVC/Reto-Estud-IA.git
cd Reto-Estud-IA

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

## 🐳 Despliegue con Docker y PostgreSQL

El entorno de contenedores orquesta la aplicación y el motor de base de datos relacional **PostgreSQL**:

- **App:** `http://localhost:8000` (Dashboard interactivo y API FastAPI).
- **PostgreSQL:** Puerto `5432` (Base de datos relacional con volumen persistente `postgres_data`).
- **Credenciales por defecto:**
  - *Usuario:* `postgres`
  - *Contraseña:* `postgres123`
  - *Base de datos:* `estudia_db`
- **Volumen de datos locales:** `./input` montado en `/app/input`.

### Levantar el entorno completo:
```bash
docker-compose up --build
```
