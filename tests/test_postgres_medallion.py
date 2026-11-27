"""Pruebas de integración para PostgreSQL, migración Alembic 0003 y Backend."""

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.modules.affiliates.service import AffiliatesService
from app.modules.analytics.service import AnalyticsService
from app.modules.eda import (
    cargar_configuracion,
    cargar_tablas_en_postgres,
    ejecutar_pipeline_completo,
    ingerir_y_validar_bronze,
    listar_tablas_medallion_db,
)
from app.modules.eda.audit import BitacoraAuditoria, filtrar_registros_rechazados
from app.modules.eda.gold import construir_fact_encuestas_bi
from app.modules.eda.models import (
    AuditEjecucionEtl,
    GoldDimEmpresa360,
    GoldDimEventoKpis,
    GoldFactEncuestasBi,
    SilverDimEmpresa,
    SilverMembresia,
)
from app.modules.retention.service import RetentionService
from migrations.versions import rev_0004_dwh_silver_3nf_gold_star as mig_0004
from tests.test_modelo_dimensional import crear_fuentes_sinteticas


def test_deteccion_archivo_modificado_mediante_hash_sha256(tmp_path: Path) -> None:
    """Verifica que Bronze registre las 7 fuentes y aborte si cambia el hash SHA-256."""
    norm_dir = tmp_path / "norm"
    dup_dir = norm_dir / "duplicados"
    out_dir = tmp_path / "input"
    crear_fuentes_sinteticas(norm_dir, dup_dir)

    cfg = cargar_configuracion(
        origen_normalizados_override=norm_dir,
        origen_duplicados_override=dup_dir,
        salida_root_override=out_dir,
    )
    _, df_hashes = ingerir_y_validar_bronze(
        cfg, run_id="RUN-TEST-01", ts_ingesta="2026-11-19 10:00:00"
    )
    assert len(df_hashes) == 7
    assert (df_hashes["id_ejecucion"] == "RUN-TEST-01").all()

    archivo_kams = norm_dir / "dim_kams.csv"
    archivo_kams.write_text(
        archivo_kams.read_text(encoding="utf-8") + "\nKAM Z,Nuevo,True,1\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="Conflicto de integridad en Bronze"):
        ingerir_y_validar_bronze(cfg, run_id="RUN-TEST-02")


def test_conservacion_registros_rechazados_en_silver() -> None:
    """Verifica que filas con PK nula o duplicada se conserven en rechazados."""
    bitacora = BitacoraAuditoria(run_id="RUN-REJ-01", fecha_corte="2026-11-13")
    df_sucio = pd.DataFrame(
        [
            {"id_empresa": "EMP-0001"},
            {"id_empresa": None},
            {"id_empresa": ""},
            {"id_empresa": "EMP-0001"},
        ]
    )
    df_limpio, rech_cnt = filtrar_registros_rechazados(
        df_sucio, "dim_empresas", ["id_empresa"], "dim_empresas.csv", bitacora
    )
    assert len(df_limpio) == 1
    assert rech_cnt == 3


def test_separacion_satisfaccion_likert_1_5_y_nps_oficial_0_10(tmp_path: Path) -> None:
    """Verifica que fact_encuestas_bi clasifique NPS 0-10 separado de Likert 1-5."""
    cfg = cargar_configuracion(salida_root_override=tmp_path / "input")
    cfg.asegurar_directorios()
    bitacora = BitacoraAuditoria(run_id="RUN-NPS-01", fecha_corte="2026-11-13")

    df_enc_silver = pd.DataFrame(
        [
            {
                "id_respuesta": "N-1",
                "id_evento": pd.NA,
                "id_persona": "P-0001",
                "id_empresa": "EMP-0001",
                "id_ciudad_encuesta": pd.NA,
                "fecha_encuesta": "2026-10-10",
                "modalidad_encuesta": "Presencial",
                "tipo_encuesta": "ENCUESTA_90_DIAS",
                "calif_locacion_o_plataforma": 5,
                "calif_convocatoria_publicidad": 5,
                "calif_conferencistas": 5,
                "calif_relevancia_temas": 5,
                "pregunta_recomendacion_nps_0_10": 10,
                "temarios_sugeridos": "Liderazgo y cultura",
                "desea_recibir_actualizaciones": True,
            },
            {
                "id_respuesta": "N-2",
                "id_evento": pd.NA,
                "id_persona": "P-0002",
                "id_empresa": "EMP-0002",
                "id_ciudad_encuesta": pd.NA,
                "fecha_encuesta": "2026-10-11",
                "modalidad_encuesta": "Presencial",
                "tipo_encuesta": "ENCUESTA_90_DIAS",
                "calif_locacion_o_plataforma": 3,
                "calif_convocatoria_publicidad": 3,
                "calif_conferencistas": 3,
                "calif_relevancia_temas": 3,
                "pregunta_recomendacion_nps_0_10": 5,
                "temarios_sugeridos": "Gracias",
                "desea_recibir_actualizaciones": False,
            },
        ]
    )
    df_bi = construir_fact_encuestas_bi(df_enc_silver, {}, cfg, bitacora)
    assert list(df_bi["categoria_nps_0_10"]) == ["PROMOTOR", "DETRACTOR"]
    assert list(df_bi["nivel_satisfaccion_1_5"]) == ["ALTA", "BAJA"]
    assert df_bi.loc[0, "categoria_tema_nlp"] == "Liderazgo y Cultura"
    assert pd.isna(df_bi.loc[1, "categoria_tema_nlp"])


def test_alembic_0004_persistencia_upsert_26_tablas_y_backend(tmp_path: Path) -> None:
    """Verifica migración 0004 (upgrade/downgrade), UPSERT de 26 tablas y Backend."""
    norm_dir = tmp_path / "norm"
    dup_dir = norm_dir / "duplicados"
    out_dir = tmp_path / "input"
    crear_fuentes_sinteticas(norm_dir, dup_dir)

    db_path = tmp_path / "test_dwh.db"
    engine = create_engine(f"sqlite:///{db_path}")

    mig_0004.upgrade(bind=engine)
    tablas_creadas = listar_tablas_medallion_db(engine)
    assert len(tablas_creadas) == 25
    assert "audit_ingestion_watermarks" in inspect(engine).get_table_names()

    cfg = cargar_configuracion(
        origen_normalizados_override=norm_dir,
        origen_duplicados_override=dup_dir,
        salida_root_override=out_dir,
    )
    res_1 = ejecutar_pipeline_completo(cfg=cfg, persistir_en_db=True, db_engine=engine)
    assert res_1["conteos_db"]["silver_dim_empresas"] == 4
    assert res_1["conteos_db"]["silver_membresias"] == 4
    assert res_1["conteos_db"]["gold_dim_empresa_360"] == 4
    assert res_1["conteos_db"]["gold_dim_evento_kpis"] == 2
    assert "audit_registros_duplicados" not in res_1["conteos_db"]

    seg_dir = out_dir / "gold" / "segmentos_comunicaciones"
    assert len(list(seg_dir.glob("*.csv"))) == 8

    res_2 = ejecutar_pipeline_completo(cfg=cfg, persistir_en_db=True, db_engine=engine)
    assert res_2["conteos_db"]["silver_dim_empresas"] == 4

    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        assert session.query(SilverDimEmpresa).count() == 4
        assert session.query(SilverMembresia).count() == 4
        assert session.query(GoldDimEmpresa360).count() == 4
        assert session.query(GoldDimEventoKpis).count() == 2
        assert session.query(GoldFactEncuestasBi).count() == 3
        assert session.query(AuditEjecucionEtl).count() >= 1

        res_aff = AffiliatesService().get_summary(session=session)
        assert res_aff["fuente_datos"] == "postgresql"
        assert res_aff["afiliados_activos_crm"] == 2
        assert res_aff["prospectos_sin_crm"] == 1

        res_ana = AnalyticsService().get_metrics(session=session)
        assert res_ana["fuente_datos"] == "postgresql"
        assert res_ana["personas_unicas_participantes"] == 2
        assert res_ana["total_respuestas_encuestas"] == 3

        res_ret = RetentionService().get_retention_overview(session=session)
        assert res_ret["fuente_datos"] == "postgresql"
        assert res_ret["membresias_activas"] == 2
        assert res_ret["retiros_definitivos_actuales"] == 1

    mig_0004.downgrade(bind=engine)
    assert len(listar_tablas_medallion_db(engine)) == 6
    assert "audit_ingestion_watermarks" in inspect(engine).get_table_names()


def test_manejo_errores_y_rollback_transaccional_db(tmp_path: Path) -> None:
    """Verifica que un fallo de clave foránea haga rollback completo."""
    db_path = tmp_path / "test_rollback.db"
    engine = create_engine(f"sqlite:///{db_path}")

    df_kams_valido = pd.DataFrame(
        [
            {
                "kam_id": "KAM A",
                "responsable_nombre": "Paula",
                "tiene_seguimiento_eventos": True,
            }
        ]
    )
    df_emp_fk_invalida = pd.DataFrame(
        [
            {
                "id_empresa": "EMP-9999",
                "kam_id": "KAM-INEXISTENTE",
                "es_empresa_activa": True,
            }
        ]
    )

    with pytest.raises(RuntimeError, match="rollback"):
        cargar_tablas_en_postgres(
            {
                "silver": {
                    "dim_kams": df_kams_valido,
                    "dim_empresas": df_emp_fk_invalida,
                }
            },
            engine=engine,
        )

    with engine.connect() as conn:
        cnt_kams = conn.execute(text("SELECT COUNT(*) FROM silver_dim_kams")).scalar()
        assert cnt_kams == 0
