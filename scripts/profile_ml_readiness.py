"""Perfila disponibilidad agregada para los cuatro casos de uso ML de ACTHO 360."""

import json
from typing import Any

from sqlalchemy import Engine, text

from app.database import get_engine

PROFILE_QUERIES: dict[str, str] = {
    "row_counts": """
        SELECT 'silver_dim_empresas' AS tabla, count(*) AS filas
        FROM silver_dim_empresas
        UNION ALL SELECT 'silver_membresias', count(*) FROM silver_membresias
        UNION ALL SELECT 'silver_fact_movimientos_crm', count(*)
        FROM silver_fact_movimientos_crm
        UNION ALL SELECT 'silver_fact_asistencias', count(*)
        FROM silver_fact_asistencias
        UNION ALL SELECT 'silver_fact_encuestas_satisfaccion', count(*)
        FROM silver_fact_encuestas_satisfaccion
        UNION ALL SELECT 'silver_dim_eventos', count(*) FROM silver_dim_eventos
        UNION ALL SELECT 'gold_dim_empresa_360', count(*) FROM gold_dim_empresa_360
        UNION ALL SELECT 'gold_fact_asistencias_bi', count(*)
        FROM gold_fact_asistencias_bi
        UNION ALL SELECT 'gold_fact_encuestas_bi', count(*)
        FROM gold_fact_encuestas_bi
        ORDER BY tabla
    """,
    "membership_status": """
        SELECT estado_membresia_detalle AS estado, count(*) AS filas,
            count(*) FILTER (WHERE fecha_inicio_vigencia IS NULL) AS sin_inicio,
            count(*) FILTER (WHERE fecha_fin_vigencia IS NULL) AS sin_fin,
            min(fecha_inicio_vigencia) AS inicio_min,
            max(fecha_fin_vigencia) AS fin_max
        FROM silver_membresias
        GROUP BY estado_membresia_detalle
        ORDER BY filas DESC
    """,
    "crm_movements": """
        SELECT tipo_movimiento, es_cierre_facturado, count(*) AS filas,
            count(*) FILTER (WHERE id_membresia IS NULL) AS sin_membresia,
            count(DISTINCT id_empresa) AS empresas
        FROM silver_fact_movimientos_crm
        GROUP BY tipo_movimiento, es_cierre_facturado
        ORDER BY tipo_movimiento, es_cierre_facturado
    """,
    "attendance_coverage": """
        SELECT count(*) AS filas,
            count(*) FILTER (WHERE id_empresa IS NULL) AS sin_empresa,
            count(*) FILTER (WHERE id_persona IS NULL) AS sin_persona,
            count(DISTINCT id_empresa) AS empresas,
            count(DISTINCT id_evento) AS eventos,
            count(*) FILTER (WHERE autoriza_tratamiento_datos IS NULL)
                AS autorizacion_desconocida
        FROM silver_fact_asistencias
    """,
    "survey_coverage": """
        SELECT count(*) AS filas,
            count(*) FILTER (WHERE id_empresa IS NULL) AS sin_empresa,
            count(*) FILTER (WHERE id_persona IS NULL) AS sin_persona,
            count(DISTINCT id_empresa) AS empresas,
            count(DISTINCT id_evento) AS eventos,
            count(*) FILTER (WHERE pregunta_recomendacion_nps_0_10 IS NULL)
                AS sin_nps,
            count(*) FILTER (
                WHERE temarios_sugeridos IS NULL OR btrim(temarios_sugeridos) = ''
            ) AS sin_texto,
            min(fecha_encuesta) AS fecha_min,
            max(fecha_encuesta) AS fecha_max
        FROM silver_fact_encuestas_satisfaccion
    """,
    "event_coverage": """
        SELECT count(*) AS eventos,
            count(DISTINCT linea_oferta_2027) AS lineas,
            count(*) FILTER (
                WHERE modalidad IS NULL OR btrim(modalidad) = ''
            ) AS sin_modalidad,
            min(fecha_inicio_evento) AS fecha_min,
            max(fecha_inicio_evento) AS fecha_max
        FROM silver_dim_eventos
    """,
    "company_population": """
        SELECT tipo_relacion_actho, count(*) AS empresas,
            count(*) FILTER (WHERE total_asistencias_anio > 0) AS con_asistencias,
            count(*) FILTER (WHERE total_ciclos_membresia > 0) AS con_ciclos,
            count(*) FILTER (WHERE total_encuestas_respondidas > 0) AS con_encuesta,
            count(*) FILTER (
                WHERE sector_economico IS NULL OR btrim(sector_economico) = ''
            ) AS sin_sector,
            count(*) FILTER (
                WHERE tamano_empresa IS NULL OR btrim(tamano_empresa) = ''
            ) AS sin_tamano
        FROM gold_dim_empresa_360
        GROUP BY tipo_relacion_actho
        ORDER BY tipo_relacion_actho
    """,
    "gold_ml_population": """
        SELECT count(*) AS empresas,
            count(*) FILTER (WHERE puntaje_riesgo_heuristico IS NOT NULL)
                AS heuristica_poblada,
            count(*) FILTER (WHERE probabilidad_churn_ml IS NOT NULL)
                AS churn_poblado,
            count(*) FILTER (WHERE score_fidelidad_ml_0_100 IS NOT NULL)
                AS fidelidad_poblada,
            count(*) FILTER (WHERE score_conversion_lead_ml_0_100 IS NOT NULL)
                AS lead_poblado,
            count(*) FILTER (WHERE linea_2027_recomendada_ml IS NOT NULL)
                AS recomendacion_poblada,
            count(*) FILTER (WHERE prob_asistencia_prox_evento_ml IS NOT NULL)
                AS asistencia_poblada
        FROM gold_dim_empresa_360
    """,
}


def profile_database(engine: Engine) -> dict[str, list[dict[str, Any]]]:
    """Ejecuta conteos y controles de cobertura sin leer identificadores personales."""
    report: dict[str, list[dict[str, Any]]] = {}
    with engine.connect() as connection:
        for name, statement in PROFILE_QUERIES.items():
            rows = connection.execute(text(statement)).mappings().all()
            report[name] = [dict(row) for row in rows]
    return report


def main() -> None:
    """Imprime un informe JSON agregado para guardar como evidencia de auditoría."""
    print(json.dumps(profile_database(get_engine()), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
