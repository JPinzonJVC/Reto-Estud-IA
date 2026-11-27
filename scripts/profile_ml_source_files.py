"""Genera un perfil agregado de Silver/Gold Parquet sin emitir datos personales."""

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

TABLES: dict[str, dict[str, Any]] = {
    "dim_empresas": {
        "layer": "silver",
        "key": ["id_empresa"],
        "columns": [
            "id_empresa",
            "sector_economico",
            "tamano_empresa",
            "vinculado_comunidades",
            "pilar_hr_estrategico",
            "pilar_mas_que_salario",
            "pilar_talento_que_elige",
            "pilar_gente_que_crece",
        ],
        "categories": ["sector_economico", "tamano_empresa"],
    },
    "membresias": {
        "layer": "silver",
        "key": ["id_membresia"],
        "columns": [
            "id_membresia",
            "id_empresa",
            "estado_membresia_detalle",
            "fecha_inicio_vigencia",
            "fecha_fin_vigencia",
        ],
        "categories": ["estado_membresia_detalle"],
    },
    "fact_movimientos_crm": {
        "layer": "silver",
        "key": ["id_movimiento"],
        "columns": [
            "id_movimiento",
            "id_empresa",
            "tipo_movimiento",
            "es_cierre_facturado",
            "fecha_cierre_o_factura",
            "fecha_expiracion_afiliacion",
        ],
        "categories": ["tipo_movimiento", "es_cierre_facturado"],
    },
    "fact_asistencias": {
        "layer": "silver",
        "key": ["id_asistencia"],
        "columns": [
            "id_asistencia",
            "id_empresa",
            "id_persona",
            "id_evento",
            "tipo_asistencia",
            "autoriza_tratamiento_datos",
        ],
        "categories": ["tipo_asistencia", "autoriza_tratamiento_datos"],
    },
    "fact_encuestas_satisfaccion": {
        "layer": "silver",
        "key": ["id_respuesta"],
        "columns": [
            "id_respuesta",
            "id_empresa",
            "id_persona",
            "id_evento",
            "fecha_encuesta",
            "pregunta_recomendacion_nps_0_10",
            "promedio_respuesta_1_5",
            "temarios_sugeridos",
            "desea_recibir_actualizaciones",
        ],
        "categories": ["tipo_encuesta", "modalidad_encuesta"],
    },
    "dim_eventos": {
        "layer": "silver",
        "key": ["id_evento"],
        "columns": [
            "id_evento",
            "fecha_inicio_evento",
            "fecha_fin_evento",
            "linea_oferta_2027",
            "modalidad",
        ],
        "categories": ["linea_oferta_2027", "modalidad"],
    },
    "dim_empresa_360": {
        "layer": "gold",
        "key": ["id_empresa"],
        "columns": [
            "id_empresa",
            "tipo_relacion_actho",
            "total_ciclos_membresia",
            "total_eventos_anio",
            "personas_distintas_anio",
            "satisfaccion_promedio_1_5",
            "nps_reciente_0_10",
            "probabilidad_churn_ml",
            "score_fidelidad_ml_0_100",
            "score_conversion_lead_ml_0_100",
            "linea_2027_recomendada_ml",
            "prob_asistencia_prox_evento_ml",
        ],
        "categories": ["tipo_relacion_actho"],
    },
}


def _profile_table(root: Path, name: str, config: dict[str, Any]) -> dict[str, Any]:
    """Resume esquema, llaves, nulos y categorías de una tabla Parquet."""
    path = root / config["layer"] / f"{name}.parquet"
    if not path.exists():
        return {"available": False}

    frame = pd.read_parquet(path)
    selected = [column for column in config["columns"] if column in frame]
    key = [column for column in config["key"] if column in frame]
    category_counts: dict[str, dict[str, int]] = {}
    for column in config["categories"]:
        if column in frame:
            values = frame[column].fillna("<NULL>").astype(str).value_counts()
            category_counts[column] = {str(k): int(v) for k, v in values.items()}

    return {
        "available": True,
        "rows": int(len(frame)),
        "columns": {column: str(frame[column].dtype) for column in selected},
        "nulls": {column: int(frame[column].isna().sum()) for column in selected},
        "duplicate_keys": (int(frame.duplicated(key).sum()) if key else None),
        "categories": category_counts,
    }


def profile_source_files(input_root: Path) -> dict[str, Any]:
    """Perfil Silver/Gold sin devolver claves o contenido de filas."""
    return {
        "input_root": str(input_root),
        "tables": {
            name: _profile_table(input_root, name, config)
            for name, config in TABLES.items()
        },
    }


def main() -> None:
    """Imprime métricas agregadas para revisión reproducible de los Parquet."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input_root",
        type=Path,
        help="Directorio Medallion que contiene las carpetas silver/ y gold/.",
    )
    arguments = parser.parse_args()
    report = profile_source_files(arguments.input_root)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
