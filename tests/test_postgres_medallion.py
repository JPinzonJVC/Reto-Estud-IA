"""Pruebas unitarias e integración para PostgreSQL, Alembic, Rechazados y Backend."""

from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
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
from app.modules.eda.gold import construir_agg_satisfaccion_encuestas
from app.modules.eda.models import (
    AuditEjecucionEtl,
    GoldAggParticipacionEmpresa,
    GoldAggRetencionEmpresa,
    GoldAggSatisfaccionEncuestas,
    SilverDimEmpresa,
)
from app.modules.retention.service import RetentionService
from migrations.versions import rev_0001_initial_medallion_actho360 as mig_0001
from tests.test_modelo_dimensional import crear_fuentes_sinteticas


def test_deteccion_archivo_modificado_mediante_hash_sha256(tmp_path: Path) -> None:
    """Verifica que Bronze registre id_ejecucion/fecha_hora y aborte si cambia el hash.

    Args:
        tmp_path: Directorio temporal de pytest.

    """
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
    assert (df_hashes["id_ejecucion"] == "RUN-TEST-01").all()
    assert (df_hashes["fecha_hora_ingesta"] == "2026-11-19 10:00:00").all()

    archivo_kams = norm_dir / "dim_kams.csv"
    archivo_kams.write_text(
        archivo_kams.read_text(encoding="utf-8") + "\nKAM Z,Nuevo,True,1,1,0,1,1,0,0,0\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="Conflicto de integridad en Bronze"):
        ingerir_y_validar_bronze(cfg, run_id="RUN-TEST-02")


def test_conservacion_registros_rechazados_en_silver() -> None:
    """Verifica que filas con PK nula o duplicada se conserven en rechazados."""
    bitacora = BitacoraAuditoria(run_id="RUN-REJ-01", fecha_corte="2026-11-13")
    df_sucio = pd.DataFrame(
        [
            {"id_empresa": "EMP-0001", "ciudad": "Bogotá"},
            {"id_empresa": None, "ciudad": "Medellín"},
            {"id_empresa": "", "ciudad": "Cali"},
            {"id_empresa": "EMP-0001", "ciudad": "Bogotá Duplicada"},
        ]
    )
    df_limpio, rech_cnt = filtrar_registros_rechazados(
        df_sucio, "dim_empresas", ["id_empresa"], "dim_empresas.csv", bitacora
    )
    assert len(df_limpio) == 1
    assert rech_cnt == 3
    assert len(bitacora.registros_rechazados) == 3
    motivos = [r["motivo_rechazo"] for r in bitacora.registros_rechazados]
    assert any("CLAVE_PRIMARIA_NULA_O_VACIA" in m for m in motivos)
    assert any("CLAVE_PRIMARIA_DUPLICADA" in m for m in motivos)


def test_preparacion_nps_0_10_cuando_existen_respuestas_validas(tmp_path: Path) -> None:
    """Verifica que Gold calcule NPS solo cuando existan respuestas 0-10 válidas.

    Args:
        tmp_path: Directorio temporal de pytest.

    """
    cfg = cargar_configuracion(salida_root_override=tmp_path / "input")
    cfg.asegurar_directorios()
    bitacora = BitacoraAuditoria(run_id="RUN-NPS-01", fecha_corte="2026-11-13")

    df_enc = pd.DataFrame(
        [
            {
                "id_respuesta": "N-1",
                "modalidad_encuesta": "Presencial",
                "periodo_mes_iso": "2026-10",
                "id_empresa": "EMP-0001",
                "id_persona": "P-0001",
                "promedio_satisfaccion": 5.0,
                "calif_locacion_o_plataforma": 5,
                "calif_convocatoria_publicidad": 5,
                "calif_conferencistas": 5,
                "calif_relevancia_temas": 5,
                "pregunta_recomendacion_nps_0_10": 10.0,
            },
            {
                "id_respuesta": "N-2",
                "modalidad_encuesta": "Presencial",
                "periodo_mes_iso": "2026-10",
                "id_empresa": "EMP-0002",
                "id_persona": "P-0002",
                "promedio_satisfaccion": 3.0,
                "calif_locacion_o_plataforma": 3,
                "calif_convocatoria_publicidad": 3,
                "calif_conferencistas": 3,
                "calif_relevancia_temas": 3,
                "pregunta_recomendacion_nps_0_10": 5.0,
            },
        ]
    )
    agg_sat = construir_agg_satisfaccion_encuestas(df_enc, cfg, bitacora)
    assert len(agg_sat) == 1
    assert agg_sat.loc[0, "nps_oficial_0_10"] == 0.0
    assert agg_sat.loc[0, "estado_calculo_nps"] == "CALCULADO_ENCUESTA_RECOMENDACION_0_10"


def test_persistencia_postgresql_upsert_idempotente_y_backend(tmp_path: Path) -> None:
    """Verifica persistencia SQL, reejecución UPSERT sin duplicados y consumo Backend.

    Args:
        tmp_path: Directorio temporal de pytest.

    """
    norm_dir = tmp_path / "norm"
    dup_dir = norm_dir / "duplicados"
    out_dir = tmp_path / "input"
    crear_fuentes_sinteticas(norm_dir, dup_dir)

    db_path = tmp_path / "test_medallion.db"
    engine = create_engine(f"sqlite:///{db_path}")

    mig_0001.upgrade(bind=engine)
    tablas_creadas = listar_tablas_medallion_db(engine)
    assert len(tablas_creadas) == 18

    cfg = cargar_configuracion(
        origen_normalizados_override=norm_dir,
        origen_duplicados_override=dup_dir,
        salida_root_override=out_dir,
    )
    res_1 = ejecutar_pipeline_completo(cfg=cfg, persistir_en_db=True, db_engine=engine)
    assert res_1["conteos_db"]["silver_dim_empresas"] == 4
    assert res_1["conteos_db"]["gold_agg_retencion_empresa"] == 4
    assert res_1["conteos_db"]["audit_registros_duplicados"] == 122

    res_2 = ejecutar_pipeline_completo(cfg=cfg, persistir_en_db=True, db_engine=engine)
    assert res_2["conteos_db"]["silver_dim_empresas"] == 4

    session_factory = sessionmaker(bind=engine)
    with session_factory() as session:
        assert session.query(SilverDimEmpresa).count() == 4
        assert session.query(GoldAggParticipacionEmpresa).count() == 4
        assert session.query(GoldAggRetencionEmpresa).count() == 4
        assert session.query(GoldAggSatisfaccionEncuestas).count() == 2
        assert session.query(AuditEjecucionEtl).count() >= 1

        aff_srv = AffiliatesService()
        res_aff = aff_srv.get_summary(session=session)
        assert res_aff["fuente_datos"] == "postgresql"
        assert res_aff["total_empresas"] == 4
        assert len(aff_srv.get_participation_list(session=session)) == 4

        ana_srv = AnalyticsService()
        res_ana = ana_srv.get_metrics(session=session)
        assert res_ana["fuente_datos"] == "postgresql"
        assert res_ana["total_respuestas_encuestas"] == 3
        assert len(ana_srv.get_satisfaction_breakdown(session=session)) == 2

        ret_srv = RetentionService()
        res_ret = ret_srv.get_retention_overview(session=session)
        assert res_ret["fuente_datos"] == "postgresql"
        assert res_ret["membresias_vencidas"] == 2
        assert res_ret["proximos_vencimientos_90d"] == 1
        assert len(ret_srv.get_companies_by_risk(session=session)) == 4


def test_manejo_errores_y_rollback_transaccional_db(tmp_path: Path) -> None:
    """Verifica que un fallo de clave foránea haga rollback completo sin corromper la DB.

    Args:
        tmp_path: Directorio temporal de pytest.

    """
    db_path = tmp_path / "test_rollback.db"
    engine = create_engine(f"sqlite:///{db_path}")

    df_kams_valido = pd.DataFrame(
        [
            {
                "kam_id": "KAM A",
                "kam_etiqueta_original": "KAM A",
                "responsable_nombre": "Paula",
                "tiene_seguimiento_eventos": True,
                "es_kam_asignado": True,
            }
        ]
    )
    df_emp_fk_invalida = pd.DataFrame(
        [
            {
                "id_empresa": "EMP-9999",
                "kam_id": "KAM-INEXISTENTE",
                "es_empresa_activa": True,
                "es_membresia_activa": True,
                "en_crm_afiliados": True,
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
