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
- [Diagrama ERM de la Base de Datos (26 Tablas: Silver 3NF + Gold Estrella + Audit)](#-diagrama-erm-de-la-base-de-datos-26-tablas-silver-3nf--gold-estrella--audit)
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
│   │   ├── eda/                           # Pipeline ETL Medallion (Bronze -> Silver -> Gold -> Audit -> PostgreSQL)
│   │   │   ├── config.py                  # Configuración portable hacia input/
│   │   │   ├── etl_config.json            # Parámetros de negocio y rutas Medallion
│   │   │   ├── bronze.py                  # Ingesta y verificación SHA-256
│   │   │   ├── scd2.py                    # Reconstrucción histórica SCD Tipo 2
│   │   │   ├── silver.py                  # Modelo dimensional puro y captura de rechazados
│   │   │   ├── gold.py                    # Agregaciones analíticas, preparación NPS y semáforo
│   │   │   ├── audit.py                   # Bitácoras de calidad, duplicados, rechazados y reconciliación
│   │   │   ├── models/                    # Paquete con los 18 modelos SQLAlchemy ORM y atributos documentados
│   │   │   ├── postgres_loader.py         # Carga masiva transaccional con UPSERT idempotente
│   │   │   └── pipeline.py                # Orquestador ejecutable del pipeline Medallion
│   │   ├── retention/                 # Módulo de Retención y Fidelización (Consume Gold)
│   │   │   ├── repository.py          # Consultas SQL/Parquet sobre gold_agg_retencion_empresa
│   │   │   ├── router.py              # Endpoints REST de retención
│   │   │   ├── service.py             # Lógica y orquestación de negocio
│   │   │   └── risk_engine.py         # Motor de riesgo y recomendaciones
│   │   ├── machine_learning/          # Pipeline y Modelos de ML
│   │   │   ├── features.py            # Ingeniería de características
│   │   │   ├── preprocessing.py       # Saneamiento y normalización
│   │   │   ├── training.py            # Entrenamiento y guardado de modelos
│   │   │   ├── prediction.py          # Inferencia (Churn y Clustering)
│   │   │   └── models/                # Artefactos serializados (.pkl)
│   │   ├── analytics/                 # Módulo de Analítica y Métricas (Consume Gold)
│   │   │   ├── repository.py          # Consultas sobre gold_agg_participacion y satisfaccion
│   │   │   ├── service.py             # Servicio de indicadores analíticos
│   │   │   └── router.py
│   │   └── affiliates/                # Módulo de Red de Afiliados (Consume Gold)
│   │       ├── repository.py          # Consultas sobre empresas afiliadas y participación
│   │       ├── service.py             # Servicio de desempeño de afiliados
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
├── migrations/                        # Migraciones Alembic del esquema Medallion
│   ├── env.py
│   └── versions/
│       └── rev_0001_initial_medallion_actho360.py
├── scripts/
│   ├── flake8_run.py                  # Script de validación PEP 8 (90 chars)
│   └── pylint_run.py                  # Script de análisis estático con pylint-exit
├── tests/                             # Suite de pruebas unitarias e integración
│   ├── test_database.py               # Pruebas de configuración y conexión a base de datos
│   ├── test_modelo_dimensional.py     # 10 pruebas del modelo dimensional Medallion
│   ├── test_postgres_medallion.py     # Pruebas de persistencia PostgreSQL, UPSERT, rollback y Backend Gold
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

## 🗄️ Diagrama ERM de la Base de Datos (26 Tablas: Silver 3NF + Gold Estrella + Audit)

El Data Warehouse de **ACTHO 360** persiste en PostgreSQL **26 tablas** estructuradas en tres capas del patrón Medallion (**13 en Silver 3NF**, **7 en Gold Esquema Estrella + ML** y **6 en Audit / Gobierno**).

### 1. Capa Silver — Core Data Warehouse (3NF — 13 Tablas)

Normaliza la jerarquía geográfica (`País → Departamento → Ciudad`), las dimensiones maestras (`KAMs`, `Empresas`, `Personas`, `Eventos`, `Catálogo de Membresía`), la relación muchos-a-muchos `Persona ↔ Empresa`, los ciclos reales de `Membresías` y las tres tablas de hechos transaccionales (`Asistencias`, `Encuestas de Satisfacción` y `Movimientos CRM`).

```mermaid
erDiagram
    SILVER_DIM_PAIS ||--o{ SILVER_DIM_DEPARTAMENTO : "contiene (id_pais)"
    SILVER_DIM_DEPARTAMENTO ||--o{ SILVER_DIM_CIUDAD : "contiene (id_departamento)"

    SILVER_DIM_KAMS ||--o{ SILVER_DIM_EMPRESAS : "gestiona (kam_id)"
    SILVER_DIM_KAMS ||--o{ SILVER_MEMBRESIAS : "responsable (kam_id)"
    SILVER_DIM_KAMS ||--o{ SILVER_FACT_ASISTENCIAS : "registra (kam_id)"
    SILVER_DIM_KAMS ||--o{ SILVER_FACT_MOVIMIENTOS_CRM : "opera (kam_id)"

    SILVER_DIM_CIUDAD ||--o{ SILVER_DIM_EMPRESAS : "sede_empresa (id_ciudad_empresa)"
    SILVER_DIM_CIUDAD ||--o{ SILVER_DIM_PERSONAS : "ubicacion_persona (id_ciudad_persona)"
    SILVER_DIM_CIUDAD ||--o{ SILVER_DIM_EVENTOS : "sede_evento (id_ciudad_evento)"
    SILVER_DIM_CIUDAD ||--o{ SILVER_FACT_ASISTENCIAS : "ciudad_asistente (id_ciudad_asistente)"
    SILVER_DIM_CIUDAD ||--o{ SILVER_FACT_ENCUESTAS_SATISFACCION : "ciudad_encuesta (id_ciudad_encuesta)"

    SILVER_DIM_EMPRESAS ||--o{ SILVER_BRIDGE_PERSONA_EMPRESA : "vincula (id_empresa)"
    SILVER_DIM_PERSONAS ||--o{ SILVER_BRIDGE_PERSONA_EMPRESA : "pertenece (id_persona)"

    SILVER_DIM_CATALOGO_MEMBRESIA ||--o{ SILVER_MEMBRESIAS : "clasifica (id_cat_membresia)"
    SILVER_DIM_CATALOGO_MEMBRESIA ||--o{ SILVER_FACT_MOVIMIENTOS_CRM : "negocia (id_cat_membresia_movimiento)"
    SILVER_DIM_EMPRESAS ||--o{ SILVER_MEMBRESIAS : "posee_ciclo (id_empresa)"

    SILVER_DIM_EVENTOS ||--o{ SILVER_FACT_ASISTENCIAS : "convoca (id_evento)"
    SILVER_DIM_PERSONAS ||--o{ SILVER_FACT_ASISTENCIAS : "asiste (id_persona)"
    SILVER_DIM_EMPRESAS ||--o{ SILVER_FACT_ASISTENCIAS : "representa (id_empresa)"
    SILVER_BRIDGE_PERSONA_EMPRESA ||--o{ SILVER_FACT_ASISTENCIAS : "valida_vinculo (id_vinculo)"

    SILVER_DIM_EVENTOS ||--o{ SILVER_FACT_ENCUESTAS_SATISFACCION : "evalua (id_evento)"
    SILVER_DIM_PERSONAS ||--o{ SILVER_FACT_ENCUESTAS_SATISFACCION : "responde (id_persona)"
    SILVER_DIM_EMPRESAS ||--o{ SILVER_FACT_ENCUESTAS_SATISFACCION : "asocia (id_empresa)"

    SILVER_DIM_EMPRESAS ||--o{ SILVER_FACT_MOVIMIENTOS_CRM : "titular (id_empresa)"
    SILVER_MEMBRESIAS ||--o{ SILVER_FACT_MOVIMIENTOS_CRM : "origina (id_membresia)"
    SILVER_DIM_PERSONAS ||--o{ SILVER_FACT_MOVIMIENTOS_CRM : "contacto (id_persona_contacto)"

    SILVER_DIM_PAIS {
        int id_pais PK
        string nombre_pais UK "NOT NULL"
    }

    SILVER_DIM_DEPARTAMENTO {
        int id_departamento PK
        int id_pais FK "NOT NULL"
        string nombre_departamento "UK(id_pais, nombre_departamento)"
    }

    SILVER_DIM_CIUDAD {
        int id_ciudad PK
        int id_departamento FK "NOT NULL"
        string nombre_ciudad "UK(id_departamento, nombre_ciudad)"
    }

    SILVER_DIM_KAMS {
        string kam_id PK "KAM A..I | KAM-UNASSIGNED"
        string responsable_nombre "NOT NULL"
        boolean tiene_seguimiento_eventos "NOT NULL"
    }

    SILVER_DIM_EMPRESAS {
        string id_empresa PK "EMP-xxxx"
        string id_registro_crm
        string kam_id FK "NOT NULL"
        int id_ciudad_empresa FK
        boolean es_empresa_activa "NOT NULL"
        string sector_economico
        string subsector_economico
        string tamano_empresa
        string rango_empleados
        float porcentaje_mujeres_num
        string fecha_ultima_actividad_crm
        boolean es_independiente
        boolean es_registro_prueba
        boolean bloqueado_crm
        boolean vinculado_comunidades
        boolean pilar_hr_estrategico
        boolean pilar_mas_que_salario
        boolean pilar_talento_que_elige
        boolean pilar_gente_que_crece
        boolean comunidad_mujeres_hr
        boolean es_influenciador
    }

    SILVER_DIM_PERSONAS {
        string id_persona PK "P-xxxxx"
        int id_ciudad_persona FK
        string nivel_cargo_actual
    }

    SILVER_BRIDGE_PERSONA_EMPRESA {
        int id_vinculo PK
        string id_persona FK "UK(id_persona, id_empresa)"
        string id_empresa FK "UK(id_persona, id_empresa)"
        string nivel_cargo
        string fecha_primera_evidencia
        string fecha_ultima_evidencia
        string fuente_relacion "CRM | ASISTENCIA | ENCUESTA"
        string estado_validacion "CONFIRMADO_CRM | REPORTADO | INFERIDO"
        boolean es_vinculo_actual "NOT NULL"
    }

    SILVER_DIM_EVENTOS {
        int id_evento PK "1..N"
        int id_ciudad_evento FK
        string nombre_evento "NOT NULL"
        string fecha_inicio_evento "NOT NULL"
        string fecha_fin_evento "NOT NULL"
        string linea_oferta_2027 "NOT NULL"
        string experiencia_detalle
        string modalidad "Presencial | Virtual | Hibrido"
    }

    SILVER_DIM_CATALOGO_MEMBRESIA {
        int id_cat_membresia PK
        string segmento_membresia "UK(segmento, nivel)"
        string nivel_membresia "UK(segmento, nivel)"
        string nombre_categoria "NOT NULL"
    }

    SILVER_MEMBRESIAS {
        string id_membresia PK "MEM-xxxx"
        string id_empresa FK "NOT NULL"
        int id_cat_membresia FK "NOT NULL"
        string kam_id FK
        string id_registro_crm_origen
        string estado_membresia_detalle "NOT NULL"
        boolean es_membresia_activa "NOT NULL"
        string fecha_miembro_desde
        string fecha_afiliacion
        string fecha_inicio_vigencia
        string fecha_fin_vigencia
    }

    SILVER_FACT_ASISTENCIAS {
        string id_asistencia PK
        int id_evento FK "NOT NULL"
        string id_persona FK
        string id_empresa FK
        int id_vinculo FK
        string kam_id FK
        int id_ciudad_asistente FK
        string nivel_cargo_evento
        string tipo_asistencia "Afiliado | No Afiliado"
        int cantidad_inscritos
        boolean tiene_costo
        boolean autoriza_tratamiento_datos
    }

    SILVER_FACT_ENCUESTAS_SATISFACCION {
        string id_respuesta PK "EP-xxxx | EV-xxxx"
        int id_evento FK
        string id_persona FK
        string id_empresa FK
        int id_ciudad_encuesta FK
        string fecha_encuesta "NOT NULL"
        string modalidad_encuesta "NOT NULL"
        string tipo_encuesta "POST_EVENTO | ENCUESTA_90_DIAS"
        int duracion_segundos
        int calif_locacion_o_plataforma "Likert 1-5"
        int calif_convocatoria_publicidad "Likert 1-5"
        int calif_conferencistas "Likert 1-5"
        int calif_relevancia_temas "Likert 1-5"
        int pregunta_recomendacion_nps_0_10 "NPS 0-10"
        text temarios_sugeridos
        boolean desea_recibir_actualizaciones
    }

    SILVER_FACT_MOVIMIENTOS_CRM {
        string id_movimiento PK "MOV-xxxx"
        string id_empresa FK "NOT NULL"
        string id_membresia FK
        string kam_id FK "NOT NULL"
        string id_persona_contacto FK
        int id_cat_membresia_movimiento FK
        string tipo_movimiento "NOT NULL"
        string estado_movimiento_crm
        boolean es_cierre_facturado "NOT NULL"
        string fecha_cierre_o_factura
        string fecha_expiracion_afiliacion
    }
```

---

### 2. Capa Gold — Esquema Estrella Analítico, BI y Machine Learning (7 Tablas)

Diseñada para consumo de baja latencia desde el Dashboard Ejecutivo y los módulos de Analítica, Retención, Afiliados y Machine Learning. Conecta las dimensiones conformadas (`gold_dim_empresa_360` y `gold_dim_evento_kpis`) con los hechos enriquecidos (`gold_fact_asistencias_bi`, `gold_fact_encuestas_bi`), la evolución mensual (`gold_fact_evolucion_membresias_mes`), el data mart de comunicaciones (`gold_mart_segmentos_comunicaciones`) y el repositorio versionado de resultados de ML (`gold_ml_resultados_empresa`).

```mermaid
erDiagram
    GOLD_DIM_EMPRESA_360 ||--o{ GOLD_FACT_ASISTENCIAS_BI : "filtra_empresa (id_empresa)"
    GOLD_DIM_EVENTO_KPIS ||--o{ GOLD_FACT_ASISTENCIAS_BI : "filtra_evento (id_evento)"

    GOLD_DIM_EMPRESA_360 ||--o{ GOLD_FACT_ENCUESTAS_BI : "evalua_empresa (id_empresa)"
    GOLD_DIM_EVENTO_KPIS ||--o{ GOLD_FACT_ENCUESTAS_BI : "evalua_evento (id_evento)"

    GOLD_DIM_EMPRESA_360 ||--o{ GOLD_MART_SEGMENTOS_COMUNICACIONES : "segmenta (id_empresa)"
    GOLD_DIM_EMPRESA_360 ||--o{ GOLD_ML_RESULTADOS_EMPRESA : "versiona_inferencia_ml (id_empresa)"

    GOLD_DIM_EMPRESA_360 {
        string id_empresa PK
        string tipo_relacion_actho "AFILIADO_ACTIVO | EX_AFILIADO | PROSPECTO_NO_AFILIADO"
        string kam_id "INDEX"
        string responsable_kam
        boolean kam_con_seguimiento
        string id_membresia_actual
        string estado_membresia_detalle
        boolean es_membresia_activa
        string segmento_membresia
        string nivel_membresia "INDEX"
        string sector_economico "INDEX"
        string subsector_economico
        string tamano_empresa
        string rango_empleados
        float porcentaje_mujeres_num
        string nombre_ciudad "INDEX"
        string nombre_departamento
        string nombre_pais
        string fecha_miembro_desde
        string fecha_afiliacion_actual
        string fecha_inicio_vigencia
        string fecha_fin_vigencia
        float dias_para_expiracion
        string tramo_vencimiento "VENCIDA | 0_30D | 31_60D | 61_90D | MAS_90D"
        int total_ciclos_membresia
        int total_eventos_anio
        int total_asistencias_anio
        int personas_distintas_anio
        int asistencias_ultimo_trimestre
        float dias_sin_participacion
        int total_encuestas_respondidas
        float satisfaccion_promedio_1_5
        float satisfaccion_reciente_1_5
        int nps_reciente_0_10
        boolean alerta_vencimiento_90d
        boolean alerta_sin_participacion_trimestre
        boolean alerta_baja_satisfaccion
        boolean alerta_monocontacto
        int puntaje_riesgo_heuristico
        float probabilidad_churn_ml
        string semaforo_riesgo_renovacion "ROJO | AMARILLO | VERDE | NO_APLICA"
        float score_fidelidad_ml_0_100
        string arquetipo_fidelidad_ml
        float score_conversion_lead_ml_0_100
        string linea_2027_mayor_participacion
        string linea_2027_recomendada_ml
        float prob_asistencia_prox_evento_ml
    }

    GOLD_DIM_EVENTO_KPIS {
        int id_evento PK
        string nombre_evento
        string fecha_inicio_evento
        string fecha_fin_evento
        string periodo_mes_iso "INDEX"
        string trimestre_iso
        string linea_oferta_2027 "INDEX"
        string experiencia_detalle
        string modalidad
        string nombre_ciudad_evento
        int total_registros_asistencia
        int total_cupos_inscritos_prov
        int personas_unicas_evento
        int empresas_unicas_evento
        int asistentes_afiliados
        int asistentes_no_afiliados
        float tasa_penetracion_afiliados_pct
        int cargos_alta_direccion
        int cargos_direccion_gerencia
        int cargos_jefatura_coordinacion
        int cargos_profesional_analista
        int cargos_otro_sin_dato
        float satisfaccion_promedio_evento_1_5
        float nps_evento_0_10
    }

    GOLD_FACT_ASISTENCIAS_BI {
        string id_asistencia PK
        int id_evento FK "NOT NULL"
        string id_empresa FK
        string id_persona "INDEX"
        int id_vinculo
        string kam_id_asistencia
        string fecha_inicio_evento
        string periodo_mes_iso "INDEX"
        string trimestre_iso
        string linea_oferta_2027
        string modalidad
        string tipo_asistencia
        string nivel_cargo_evento
        string nombre_ciudad_asistente
        int cantidad_inscritos_prov
        boolean tiene_costo
        boolean autoriza_tratamiento_datos
    }

    GOLD_FACT_ENCUESTAS_BI {
        string id_respuesta PK
        int id_evento FK
        string id_empresa FK
        string id_persona
        string fecha_encuesta
        string periodo_mes_iso "INDEX"
        string trimestre_iso
        string tipo_encuesta "INDEX"
        string modalidad_encuesta "INDEX"
        string nombre_ciudad_encuesta
        int calif_locacion_o_plataforma
        int calif_convocatoria_publicidad
        int calif_conferencistas
        int calif_relevancia_temas
        float promedio_respuesta_1_5
        string nivel_satisfaccion_1_5 "ALTA | MEDIA | BAJA"
        int pregunta_recomendacion_nps_0_10
        string categoria_nps_0_10 "PROMOTOR | PASIVO | DETRACTOR"
        text temarios_sugeridos
        string categoria_tema_nlp "INDEX"
        boolean desea_recibir_actualizaciones
    }

    GOLD_FACT_EVOLUCION_MEMBRESIAS_MES {
        string id_evolucion_mes PK "periodo::kam::segmento::nivel"
        string periodo_mes_iso "INDEX"
        string kam_id "INDEX"
        string segmento_membresia
        string nivel_membresia
        int altas_nuevas_mes
        int vencimientos_programados_mes
        int renovaciones_efectivas_mes
        int retiros_cancelaciones_mes
    }

    GOLD_MART_SEGMENTOS_COMUNICACIONES {
        string id_registro_segmento PK "segmento::id_empresa::id_persona"
        int orden_segmento "1..8"
        string segmento_codigo "INDEX"
        string segmento_nombre
        string id_empresa FK
        string id_persona "INDEX"
        string rol_contacto_resuelto
        string kam_id "INDEX"
        string nivel_membresia
        string sector_economico
        string nombre_ciudad
        string semaforo_riesgo_renovacion
        string linea_2027_recomendada_ml
        string categoria_tema_interes
        text detalle_criterio
        boolean autoriza_tratamiento_datos
        boolean apto_envio_comunicaciones "Habeas Data"
    }

    GOLD_ML_RESULTADOS_EMPRESA {
        int id PK
        string caso_uso "UK(caso, empresa, version, corte)"
        string id_empresa "INDEX"
        string id_ejecucion
        string version_modelo
        string fecha_corte
        string estado_evaluacion "INDEX"
        string metodo
        float score
        string segmento
        int soporte
        json justificacion
        json metricas
        string hash_dataset
        datetime creado_en
        datetime actualizado_en
    }
```

---

### 3. Capa Audit — Gobierno, Linaje, Calidad y Watermarks (6 Tablas)

Garantiza trazabilidad de punta a punta de cada corrida del pipeline ETL (`audit_ejecuciones_etl`), verificación criptográfica SHA-256 en Bronze (`audit_hashes_fuentes_bronze`), bitácora por paso (`audit_cargas`), cuarentena de rechazados (`audit_registros_rechazados`), reglas de calidad (`audit_calidad_datos`), cuadre exacto de filas (`audit_reconciliacion_origen_destino`) y cursores de sincronización incremental (`audit_ingestion_watermarks`).

```mermaid
erDiagram
    AUDIT_EJECUCIONES_ETL ||--o{ AUDIT_HASHES_FUENTES_BRONZE : "verifica_archivos (id_ejecucion)"
    AUDIT_EJECUCIONES_ETL ||--o{ AUDIT_CARGAS : "registra_pasos (id_ejecucion)"
    AUDIT_EJECUCIONES_ETL ||--o{ AUDIT_REGISTROS_RECHAZADOS : "aisla_rechazos (id_ejecucion)"

    AUDIT_EJECUCIONES_ETL {
        string id_ejecucion PK
        string fecha_inicio "NOT NULL"
        string fecha_finalizacion "NOT NULL"
        int archivos_procesados
        int registros_leidos
        int registros_cargados
        int registros_rechazados
        int duplicados_identificados
        text errores
        string estado_ejecucion "EXITOSO | FALLIDO"
    }

    AUDIT_HASHES_FUENTES_BRONZE {
        string tabla_fuente PK
        string id_ejecucion
        string fecha_hora_ingesta
        string archivo_nombre
        int bytes_origen
        int filas_leidas
        int columnas_leidas
        string sha256_origen
        string sha256_bronze
        boolean integridad_verificada
        string accion_bronze
    }

    AUDIT_CARGAS {
        string id_ejecucion PK
        string fuente PK "origen -> destino"
        string fecha_inicio
        string fecha_finalizacion
        int registros_leidos
        int registros_procesados
        int registros_insertados
        int registros_actualizados
        int registros_rechazados
        string estado_ejecucion
    }

    AUDIT_REGISTROS_RECHAZADOS {
        string id_rechazo PK "REJ-xxxx"
        string id_ejecucion
        string tabla_destino
        string archivo_origen_bronze
        text motivo_rechazo
        text registro_original_json
        string fecha_corte_modelo
    }

    AUDIT_CALIDAD_DATOS {
        string id_incidencia PK "DQ-xxxx"
        string tabla_analizada
        string campo_afectado
        string tipo_inconsistencia
        int registros_afectados
        text valor_original
        text valor_corregido
        string fecha_corte_modelo
        string estado_resolucion
    }

    AUDIT_RECONCILIACION_ORIGEN_DESTINO {
        string Tabla PK
        int Filas_Bronze
        int Cols_Bronze
        int Filas_Silver
        int Cols_Silver
        int Filas_Rechazadas
        int Diferencia_Filas "Debe ser 0"
        text Explicacion_Reconciliacion
    }

    AUDIT_INGESTION_WATERMARKS {
        string source_name PK "google_drive | zoho_crm:*"
        string last_sync_at
        string last_cursor
        string last_status "SUCCESS | SKIPPED | FAILED"
        int records_extracted
        text details
        string updated_at
    }
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
