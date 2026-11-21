"""Pruebas unitarias de ingesta cruda en Bronze y normalización en Silver."""

from pathlib import Path

import pandas as pd

from app.modules.eda.bronze import ingerir_fuentes_crudas_bronze
from app.modules.eda.config import cargar_configuracion
from app.modules.eda.normalizer import (
    leer_y_normalizar_evento_raw,
    limpiar_texto_y_mojibake,
    normalizar_booleano,
    normalizar_encabezado_snake_case,
    normalizar_fecha_iso,
)


def test_normalizar_texto_y_encabezados() -> None:
    """Valida limpieza de mojibake y conversión de encabezados a snake_case."""
    assert limpiar_texto_y_mojibake("  BogotÃ¡  D.C. ") == "Bogotá D.C."
    assert limpiar_texto_y_mojibake("   ") is None
    assert (
        normalizar_encabezado_snake_case("Nivel de cargo [anonimizado]")
        == "nivel_de_cargo"
    )
    assert (
        normalizar_encabezado_snake_case("Subsector Económico [anonimizado]")
        == "subsector_economico"
    )


def test_normalizar_booleanos_y_fechas_iso() -> None:
    """Valida estandarización de booleanos y fechas en español a ISO."""
    assert normalizar_booleano("Con costo") is True
    assert normalizar_booleano("Sin costo") is False
    assert (
        normalizar_booleano("SÍ, AUTORIZO EL TRATAMIENTO DE MIS DATOS PERSONALES") is True
    )
    assert normalizar_booleano("NO") is False
    assert normalizar_fecha_iso("mar. 20, 2025 09:21:35 a. m.") == "2025-03-20"
    assert normalizar_fecha_iso("2026-11-13") == "2026-11-13"


def test_ingesta_raw_bronze_y_normalizacion_evento(tmp_path: Path) -> None:
    """Valida ingesta de CSV crudos en Bronze y lectura normalizada en Silver."""
    raw_dir = tmp_path / "CSV"
    ev_dir = raw_dir / "Asistencia eventos"
    ev_dir.mkdir(parents=True)

    evento_csv = ev_dir / "MARZO 17.csv"
    evento_csv.write_text(
        "Semana del Talento,,,,\n"
        "AFILIADO,ID_EMPRESA,NOMBRE [eliminado],Costo [anonimizado],CIUDAD\n"
        "1,EMP-0001,Juan,Con costo,BogotÃ¡\n"
        "0,EMP-0002,Ana,Sin costo,MedellÃ­n\n",
        encoding="utf-8",
    )

    cfg = cargar_configuracion(
        origen_normalizados_override=tmp_path / "norm",
        salida_root_override=tmp_path / "out",
        origen_raw_csv_override=raw_dir,
    )
    df_hashes = ingerir_fuentes_crudas_bronze(cfg, run_id="RUN-TEST-RAW")
    assert len(df_hashes) == 1
    assert df_hashes["integridad_verificada"].all()
    assert (cfg.bronze_raw_dir / "Asistencia eventos" / "MARZO 17.csv").exists()

    df_norm = leer_y_normalizar_evento_raw(
        cfg.bronze_raw_dir / "Asistencia eventos" / "MARZO 17.csv"
    )
    assert isinstance(df_norm, pd.DataFrame)
    assert len(df_norm) == 2
    assert "nombre" not in df_norm.columns
    assert list(df_norm["tiene_costo"]) == [True, False]
