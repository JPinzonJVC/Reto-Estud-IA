"""Suite de pruebas para el Data Warehouse Silver (13 tablas) y Gold Estrella (6)."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.modules.eda import (
    cargar_configuracion,
    ejecutar_pipeline_completo,
    guardar_tabla_medallion,
)


def _fila_empresa_sintetica(
    id_emp: str,
    id_crm: str | None,
    kam_id: str,
    activa: bool,
    estado: str,
    *,
    f_afil: str | None = None,
    f_exp: str | None = None,
    en_crm: bool = True,
) -> dict[str, Any]:
    """Crea un diccionario de empresa sintética para pruebas del ETL."""
    return {
        "id_empresa": id_emp,
        "id_registro_crm": id_crm,
        "kam_id": kam_id,
        "es_empresa_activa": activa,
        "es_membresia_activa": activa,
        "estado_membresia_detalle": estado,
        "segmento_membresia": "Corporativa / Empresa",
        "nivel_membresia": "Premium" if activa else "Estándar",
        "tipo_membresia_original": "Empresa",
        "categoria_membresia_original": "Premium" if activa else "Estándar",
        "sector_economico": "Tecnología",
        "subsector_economico": "Software",
        "tamano_empresa": "Grande",
        "rango_empleados": "201-1.000",
        "porcentaje_mujeres_num": 45,
        "ciudad": "Bogotá",
        "region_departamento": "Bogotá D.C.",
        "pais": "Colombia",
        "fecha_afiliacion": f_afil,
        "fecha_expiracion": f_exp,
        "fecha_miembro_desde": "2020-01-01" if en_crm else None,
        "fecha_ultima_actividad": "2026-10-15" if en_crm else None,
        "fecha_hora_ultima_actividad": "2026-10-15 10:00:00" if en_crm else None,
        "fecha_cambio_registro": "2026-10-15" if en_crm else None,
        "fecha_hora_cambio_registro": "2026-10-15 10:00:00" if en_crm else None,
        "es_independiente": False,
        "es_registro_prueba": False,
        "bloqueado_crm": False,
        "vinculado_comunidades": activa,
        "pilar_hr_estrategico": activa,
        "pilar_mas_que_salario": False,
        "pilar_talento_que_elige": activa,
        "pilar_gente_que_crece": False,
        "comunidad_mujeres_hr": False,
        "es_influenciador": False,
        "en_crm_afiliados": en_crm,
    }


def crear_fuentes_sinteticas(norm_dir: Path, dup_dir: Path) -> None:
    """Crea las 7 fuentes normalizadas sintéticas y un ciclo histórico real."""
    norm_dir.mkdir(parents=True, exist_ok=True)
    dup_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {
                "kam_id": "KAM A",
                "responsable_nombre": "Paula",
                "tiene_seguimiento_eventos": True,
                "total_registros_afiliados": 10,
            },
            {
                "kam_id": "KAM B",
                "responsable_nombre": "Priscilla",
                "tiene_seguimiento_eventos": True,
                "total_registros_afiliados": 12,
            },
            {
                "kam_id": "Sin asignar (cuenta ACTHO)",
                "responsable_nombre": "Corporativo",
                "tiene_seguimiento_eventos": False,
                "total_registros_afiliados": 5,
            },
        ]
    ).to_csv(norm_dir / "dim_kams.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            _fila_empresa_sintetica(
                "EMP-0001",
                "R-0001",
                "KAM A",
                True,
                "Activo",
                f_afil="2024-01-15",
                f_exp="2026-12-31",
            ),
            _fila_empresa_sintetica(
                "EMP-0002",
                "R-0002",
                "KAM B",
                True,
                "Activo",
                f_afil="2026-10-01",
                f_exp="2027-09-30",
            ),
            _fila_empresa_sintetica(
                "EMP-0174",
                "R-0175",
                "Sin asignar (cuenta ACTHO)",
                False,
                "Cancelado",
                f_afil="2066-12-01",
                f_exp="2025-12-31",
            ),
            _fila_empresa_sintetica(
                "EMP-1500",
                None,
                "Sin asignar",
                False,
                "Sin membresía en CRM",
                en_crm=False,
            ),
        ]
    ).to_csv(norm_dir / "dim_empresas.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "id_duplicado": "DUP-0001",
                "id_registro_principal": "R-0001",
                "id_registro_duplicado": "R-0001-OLD",
                "id_empresa": "EMP-0001",
                "estado_membresia_duplicado": "Cancelado",
                "tipo_membresia_duplicado": "Empresa",
                "categoria_duplicada": "Estándar",
                "fecha_afiliacion_principal": "2024-01-15",
                "fecha_afiliacion_duplicada": "2021-01-15",
                "fecha_expiracion_principal": "2026-12-31",
                "fecha_expiracion_duplicada": "2023-12-31",
            }
        ]
    ).to_csv(
        dup_dir / "duplicados_afiliados_crm.csv",
        index=False,
        encoding="utf-8-sig",
    )

    pd.DataFrame(
        [
            {
                "id_persona": "P-0001",
                "id_empresa_principal": "EMP-0001",
                "nivel_cargo": "Dirección / Gerencia",
                "ciudad": "Bogotá",
                "fecha_afiliacion_nueva": None,
            },
            {
                "id_persona": "P-0002",
                "id_empresa_principal": None,
                "nivel_cargo": "Profesional / Analista / Consultor",
                "ciudad": "Cali",
                "fecha_afiliacion_nueva": None,
            },
        ]
    ).to_csv(norm_dir / "dim_personas.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "id_evento": 1,
                "archivo_csv": "MARZO 17.csv",
                "fecha_evento": "2026-03-17",
                "fecha_inicio_evento": "2026-03-17",
                "fecha_fin_evento": "2026-03-20",
                "nombre_evento": "Taller Talento (Bogotá)",
                "linea_oferta_2027": "Evento grande",
                "experiencia_detalle": "Congreso",
                "modalidad": "Presencial",
            },
            {
                "id_evento": 2,
                "archivo_csv": "SEPTIEMBRE 16.csv",
                "fecha_evento": "2026-09-16",
                "fecha_inicio_evento": "2026-09-16",
                "fecha_fin_evento": "2026-09-16",
                "nombre_evento": "Foro Liderazgo",
                "linea_oferta_2027": "Foro",
                "experiencia_detalle": "Foro",
                "modalidad": "Virtual",
            },
        ]
    ).to_csv(norm_dir / "dim_eventos.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "id_asistencia": "A-00001",
                "id_evento": 1,
                "id_empresa": "EMP-0001",
                "id_persona": "P-0001",
                "kam_id": "KAM A",
                "fecha_evento": "2026-03-17",
                "nivel_cargo": "Dirección / Gerencia",
                "ciudad_evento": "Bogotá",
                "cantidad_inscritos": 3,
                "es_afiliado": True,
                "tiene_costo": True,
                "autoriza_tratamiento_datos": True,
            },
            {
                "id_asistencia": "A-00002",
                "id_evento": 2,
                "id_empresa": "EMP-0002",
                "id_persona": "P-0001",
                "kam_id": "KAM B",
                "fecha_evento": "2026-09-16",
                "nivel_cargo": "Alta dirección (C-level / VP)",
                "ciudad_evento": "Bogotá",
                "cantidad_inscritos": 1,
                "es_afiliado": True,
                "tiene_costo": False,
                "autoriza_tratamiento_datos": True,
            },
            {
                "id_asistencia": "A-00003",
                "id_evento": 1,
                "id_empresa": "EMP-1500",
                "id_persona": "P-0002",
                "kam_id": "Sin asignar",
                "fecha_evento": "2026-03-17",
                "nivel_cargo": "Profesional / Analista / Consultor",
                "ciudad_evento": "Cali",
                "cantidad_inscritos": 1,
                "es_afiliado": False,
                "tiene_costo": False,
                "autoriza_tratamiento_datos": True,
            },
            {
                "id_asistencia": "A-00004",
                "id_evento": 2,
                "id_empresa": None,
                "id_persona": "P-0002",
                "kam_id": "Sin asignar (cuenta ACTHO)",
                "fecha_evento": "2026-09-16",
                "nivel_cargo": "Profesional / Analista / Consultor",
                "ciudad_evento": None,
                "cantidad_inscritos": 1,
                "es_afiliado": False,
                "tiene_costo": False,
                "autoriza_tratamiento_datos": True,
            },
        ]
    ).to_csv(norm_dir / "fact_asistencias.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "id_respuesta": "EP-0001",
                "modalidad_encuesta": "Presencial",
                "fecha_encuesta": "2026-03-18",
                "duracion_segundos": 120,
                "calif_locacion_o_plataforma": 5,
                "calif_convocatoria_publicidad": 5,
                "calif_conferencistas": 5,
                "calif_relevancia_temas": 5,
                "temarios_sugeridos": "Inteligencia Artificial aplicada a HR",
                "desea_recibir_actualizaciones": True,
                "id_persona": "P-0001",
                "id_empresa": "EMP-0001",
                "ciudad": "Bogotá",
                "metodo_asignacion_empresa": "Dominio del correo",
            },
            {
                "id_respuesta": "EV-0001",
                "modalidad_encuesta": "Virtual",
                "fecha_encuesta": "2026-09-17",
                "duracion_segundos": 90,
                "calif_locacion_o_plataforma": 3,
                "calif_convocatoria_publicidad": 3,
                "calif_conferencistas": 3,
                "calif_relevancia_temas": 3,
                "temarios_sugeridos": "Reforma laboral 2026",
                "desea_recibir_actualizaciones": True,
                "id_persona": "P-0002",
                "id_empresa": "EMP-0002",
                "ciudad": "Huy",
                "metodo_asignacion_empresa": "Nombre de empresa",
            },
            {
                "id_respuesta": "EP-0002",
                "modalidad_encuesta": "Presencial",
                "fecha_encuesta": "2026-03-18",
                "duracion_segundos": 60,
                "calif_locacion_o_plataforma": 4,
                "calif_convocatoria_publicidad": 4,
                "calif_conferencistas": 5,
                "calif_relevancia_temas": 5,
                "temarios_sugeridos": None,
                "desea_recibir_actualizaciones": False,
                "id_persona": None,
                "id_empresa": None,
                "ciudad": None,
                "metodo_asignacion_empresa": "Sin datos",
            },
        ]
    ).to_csv(
        norm_dir / "fact_encuestas_satisfaccion.csv",
        index=False,
        encoding="utf-8-sig",
    )

    pd.DataFrame(
        [
            {
                "tipo_movimiento": "Renovación (Últ. 2 Meses)",
                "es_cierre_facturado": True,
                "fecha_cierre_o_factura": "2026-09-01",
                "fecha_expiracion_afiliacion": "2026-12-31",
                "kam_id": "KAM A",
                "id_empresa": "EMP-0001",
                "nivel_membresia": "Premium",
                "id_persona_contacto": "P-0001",
            },
            {
                "tipo_movimiento": "Trato en Estado",
                "es_cierre_facturado": False,
                "fecha_cierre_o_factura": None,
                "fecha_expiracion_afiliacion": None,
                "kam_id": "Sin asignar",
                "id_empresa": "EMP-1500",
                "nivel_membresia": "Estándar",
                "id_persona_contacto": None,
            },
        ]
    ).to_csv(
        norm_dir / "fact_movimientos_crm.csv",
        index=False,
        encoding="utf-8-sig",
    )


@pytest.fixture(name="entorno_sintetico_etl", scope="module")
def fixture_entorno_sintetico_etl(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Any]:
    """Ejecuta el ETL DWH v3 sobre datos sintéticos en un directorio aislado."""
    base_tmp = tmp_path_factory.mktemp("actho360_dwh_env")
    norm_dir = base_tmp / "origen_normalizados"
    dup_dir = norm_dir / "duplicados"
    out_dir = base_tmp / "input"

    crear_fuentes_sinteticas(norm_dir, dup_dir)
    cfg = cargar_configuracion(
        origen_normalizados_override=norm_dir,
        origen_duplicados_override=dup_dir,
        salida_root_override=out_dir,
    )
    res_1 = ejecutar_pipeline_completo(cfg=cfg)
    return {
        "cfg": cfg,
        "res_1": res_1,
        "bronze_dir": cfg.bronze_dir,
        "silver_dir": cfg.silver_dir,
        "gold_dir": cfg.gold_dir,
        "audit_dir": cfg.audit_dir,
    }


def test_01_trece_tablas_silver_y_seis_tablas_gold_con_pks_unicas(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Valida que existan las 13 tablas Silver, 6 Gold y sin tabla de repetidos."""
    s_dir: Path = entorno_sintetico_etl["silver_dir"]
    g_dir: Path = entorno_sintetico_etl["gold_dir"]
    a_dir: Path = entorno_sintetico_etl["audit_dir"]

    assert not (a_dir / "audit_registros_duplicados.parquet").exists()
    assert not (s_dir / "dim_empresas_scd2.parquet").exists()

    pks = [
        (s_dir / "dim_pais.parquet", ["id_pais"]),
        (s_dir / "dim_departamento.parquet", ["id_departamento"]),
        (s_dir / "dim_ciudad.parquet", ["id_ciudad"]),
        (s_dir / "dim_kams.parquet", ["kam_id"]),
        (s_dir / "dim_empresas.parquet", ["id_empresa"]),
        (s_dir / "dim_catalogo_membresia.parquet", ["id_cat_membresia"]),
        (s_dir / "membresias.parquet", ["id_membresia"]),
        (s_dir / "dim_personas.parquet", ["id_persona"]),
        (s_dir / "bridge_persona_empresa.parquet", ["id_vinculo"]),
        (s_dir / "dim_eventos.parquet", ["id_evento"]),
        (s_dir / "fact_asistencias.parquet", ["id_asistencia"]),
        (s_dir / "fact_encuestas_satisfaccion.parquet", ["id_respuesta"]),
        (s_dir / "fact_movimientos_crm.parquet", ["id_movimiento"]),
        (g_dir / "dim_empresa_360.parquet", ["id_empresa"]),
        (g_dir / "dim_evento_kpis.parquet", ["id_evento"]),
        (g_dir / "fact_asistencias_bi.parquet", ["id_asistencia"]),
        (g_dir / "fact_encuestas_bi.parquet", ["id_respuesta"]),
        (g_dir / "fact_evolucion_membresias_mes.parquet", ["id_evolucion_mes"]),
        (g_dir / "mart_segmentos_comunicaciones.parquet", ["id_registro_segmento"]),
    ]
    for ruta, cols_pk in pks:
        assert ruta.exists(), f"Falta tabla {ruta.name}"
        df = pd.read_parquet(ruta)
        for col in cols_pk:
            assert df[col].isna().sum() == 0
        assert df.duplicated(subset=cols_pk).sum() == 0


def test_02_reglas_silver_membresias_puente_eventos_y_fks_opcionales(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Valida reglas de negocio en membresías, bridge N:N, asistencias y tratos CRM."""
    s_dir: Path = entorno_sintetico_etl["silver_dir"]
    df_mem = pd.read_parquet(s_dir / "membresias.parquet")
    df_br = pd.read_parquet(s_dir / "bridge_persona_empresa.parquet")
    df_ev = pd.read_parquet(s_dir / "dim_eventos.parquet")
    df_asi = pd.read_parquet(s_dir / "fact_asistencias.parquet")
    df_enc = pd.read_parquet(s_dir / "fact_encuestas_satisfaccion.parquet")
    df_mov = pd.read_parquet(s_dir / "fact_movimientos_crm.parquet")

    assert "EMP-1500" not in set(df_mem["id_empresa"])
    assert len(df_mem[df_mem["id_empresa"] == "EMP-0001"]) == 2
    mem_174 = df_mem[df_mem["id_empresa"] == "EMP-0174"].iloc[0]
    assert pd.isna(mem_174["fecha_afiliacion"])

    br_p1 = df_br[df_br["id_persona"] == "P-0001"]
    assert len(br_p1) == 2
    assert int(br_p1["es_vinculo_actual"].sum()) == 1

    assert "fecha_evento" not in df_ev.columns
    assert pd.notna(df_ev.loc[df_ev["id_evento"] == 1, "id_ciudad_evento"].iloc[0])
    assert pd.isna(df_ev.loc[df_ev["id_evento"] == 2, "id_ciudad_evento"].iloc[0])

    assert "es_afiliado" not in df_asi.columns
    a_sin_emp = df_asi[df_asi["id_asistencia"] == "A-00004"].iloc[0]
    assert pd.isna(a_sin_emp["id_vinculo"])
    assert pd.isna(a_sin_emp["kam_id"])

    assert "promedio_satisfaccion" not in df_enc.columns
    enc_huy = df_enc[df_enc["id_respuesta"] == "EV-0001"].iloc[0]
    assert pd.isna(enc_huy["id_ciudad_encuesta"])

    trato = df_mov[df_mov["tipo_movimiento"] == "Trato en Estado"].iloc[0]
    assert pd.isna(trato["id_membresia"])


def test_03_gold_eventos_sin_ceros_nlp_ml_y_reconciliacion(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Verifica conteos reales en eventos Gold, separación NPS, ML y reconciliación."""
    g_dir: Path = entorno_sintetico_etl["gold_dir"]
    a_dir: Path = entorno_sintetico_etl["audit_dir"]

    ev_kpis = pd.read_parquet(g_dir / "dim_evento_kpis.parquet")
    assert int(ev_kpis["total_registros_asistencia"].sum()) == 4
    assert int(ev_kpis["total_cupos_inscritos_prov"].sum()) == 6

    enc_bi = pd.read_parquet(g_dir / "fact_encuestas_bi.parquet")
    assert enc_bi["categoria_nps_0_10"].isna().all()
    temas = set(enc_bi["categoria_tema_nlp"].dropna())
    assert "IA y Tecnología HR" in temas
    assert "Derecho Laboral y Reforma" in temas

    emp_360 = pd.read_parquet(g_dir / "dim_empresa_360.parquet")
    act = emp_360[emp_360["tipo_relacion_actho"] == "AFILIADO_ACTIVO"]
    lead = emp_360[emp_360["tipo_relacion_actho"] == "PROSPECTO_NO_AFILIADO"]
    assert set(act["semaforo_riesgo_renovacion"]).issubset({"ROJO", "AMARILLO", "VERDE"})
    assert (lead["semaforo_riesgo_renovacion"] == "NO_APLICA").all()
    for col_ml in (
        "probabilidad_churn_ml",
        "score_fidelidad_ml_0_100",
        "arquetipo_fidelidad_ml",
        "score_conversion_lead_ml_0_100",
        "linea_2027_recomendada_ml",
        "prob_asistencia_prox_evento_ml",
    ):
        assert col_ml in emp_360.columns
        assert emp_360[col_ml].isna().all()

    reconc = pd.read_parquet(a_dir / "audit_reconciliacion_origen_destino.parquet")
    assert len(reconc) == 7
    assert (reconc["Diferencia_Filas"] == 0).all()


def test_04_idempotencia_y_fallo_parquet(
    entorno_sintetico_etl: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica idempotencia del ETL y manejo explícito de fallos Parquet."""
    cfg = entorno_sintetico_etl["cfg"]
    s_dir: Path = entorno_sintetico_etl["silver_dir"]
    snap_1 = pd.read_parquet(s_dir / "dim_empresas.parquet")

    res_2 = ejecutar_pipeline_completo(cfg=cfg)
    assert (
        res_2["hashes_bronze"]["accion_bronze"]
        == "CONSERVADO_SIN_SOBRESCRIBIR_HASH_IDENTICO"
    ).all()
    pd.testing.assert_frame_equal(
        snap_1, pd.read_parquet(s_dir / "dim_empresas.parquet"), check_exact=True
    )

    def fake_to_parquet(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("Fallo simulado de motor Parquet")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fake_to_parquet)
    with pytest.raises(RuntimeError, match="Error al generar archivo Parquet"):
        guardar_tabla_medallion(pd.DataFrame({"a": [1]}), tmp_path, "tabla_fallida")
