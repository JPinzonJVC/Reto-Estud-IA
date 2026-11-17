"""Transformaciones de la capa Silver (Dimensiones puras, SCD2 y Hechos)."""

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from app.modules.eda.audit import BitacoraAuditoria
from app.modules.eda.bronze import guardar_tabla_medallion, homologar_kam_id
from app.modules.eda.config import ConfiguracionETL
from app.modules.eda.scd2 import construir_dim_empresas_scd2

COLS_DESCRIPTIVAS_EMPRESA: tuple[str, ...] = (
    "id_empresa",
    "id_registro_crm",
    "kam_id",
    "kam_valor_original",
    "es_empresa_activa",
    "es_membresia_activa",
    "estado_membresia_detalle",
    "segmento_membresia",
    "nivel_membresia",
    "tipo_membresia_original",
    "categoria_membresia_original",
    "sector_economico",
    "subsector_economico",
    "tamano_empresa",
    "rango_empleados",
    "porcentaje_mujeres_num",
    "ciudad",
    "region_departamento",
    "pais",
    "fecha_afiliacion",
    "fecha_expiracion",
    "fecha_miembro_desde",
    "fecha_ultima_actividad",
    "fecha_hora_ultima_actividad",
    "fecha_cambio_registro",
    "fecha_hora_cambio_registro",
    "es_independiente",
    "es_registro_prueba",
    "bloqueado_crm",
    "vinculado_comunidades",
    "pilar_hr_estrategico",
    "pilar_mas_que_salario",
    "pilar_talento_que_elige",
    "pilar_gente_que_crece",
    "comunidad_mujeres_hr",
    "es_influenciador",
    "en_crm_afiliados",
)


def _procesar_dim_kams(
    bronze: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye dim_kams en Silver y separa métricas de origen a Audit.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría activa.

    Returns:
        DataFrame depurado de dim_kams.

    """
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_kams_orig = bronze["dim_kams"].copy()
    cols_metricas = [
        c
        for c in (
            "kam_id",
            "total_registros_afiliados",
            "afiliados_activos",
            "cuentas_elite_premium",
            "empresas_seguimiento_asistencia",
            "empresas_que_asistieron",
            "tratos_en_estado",
            "nuevas_afiliaciones_ult_2m",
            "renovaciones_ult_2m",
        )
        if c in df_kams_orig.columns
    ]
    guardar_tabla_medallion(
        df_kams_orig[cols_metricas], cfg.audit_dir, "audit_metricas_origen_kams"
    )

    kam_hom = df_kams_orig["kam_id"].apply(lambda v: homologar_kam_id(v, cfg))
    df_kams_silver = pd.DataFrame(
        {
            "kam_id": kam_hom,
            "kam_etiqueta_original": df_kams_orig["kam_id"],
            "responsable_nombre": df_kams_orig["responsable_nombre"],
            "tiene_seguimiento_eventos": df_kams_orig["tiene_seguimiento_eventos"].astype(
                bool
            ),
            "es_kam_asignado": kam_hom != cfg.kam_sin_asignar_id,
        }
    )
    guardar_tabla_medallion(df_kams_silver, cfg.silver_dir, "dim_kams")
    bitacora.registrar_calidad(
        "dim_kams",
        "kam_id",
        tipo_inc="IDENTIFICADOR_DESCRIPTIVO_NO_CANONICO",
        val_orig="Sin asignar (cuenta ACTHO)",
        val_corr=cfg.kam_sin_asignar_id,
        estado="CORREGIDO_HOMOLOGADO",
        cant=1,
    )
    bitacora.registrar_calidad(
        "dim_kams",
        "total_registros_afiliados..renovaciones_ult_2m",
        tipo_inc="METRICAS_AGREGADAS_EN_DIMENSION",
        val_orig="8 columnas de métricas en dim_kams",
        val_corr="Separadas a audit_metricas_origen_kams y calculadas desde hechos",
        estado="REFACTORIZADO",
        cant=len(df_kams_orig),
    )
    bitacora.registrar_carga(
        "bronze/dim_kams -> silver/dim_kams",
        t0,
        leidos=len(df_kams_orig),
        proc=len(df_kams_silver),
        ins=len(df_kams_silver),
        act=1,
    )
    return df_kams_silver


def _procesar_dim_empresas(
    bronze: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construye dim_empresas y dim_empresas_scd2 en la capa Silver.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría activa.

    Returns:
        Tupla con (df_emp_silver, df_emp_scd2).

    """
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_emp_orig = bronze["dim_empresas"].copy()
    cols_metricas = [
        c
        for c in (
            "id_empresa",
            "en_seguimiento_kam",
            "asistio_segun_kam",
            "en_matriz_general",
            "asistio_eventos_2026",
            "eventos_asistidos_reales",
            "participaciones_reales",
            "eventos_reportados_kam",
            "eventos_reportados_matriz",
            "respuestas_encuestas",
        )
        if c in df_emp_orig.columns
    ]
    guardar_tabla_medallion(
        df_emp_orig[cols_metricas], cfg.audit_dir, "audit_metricas_origen_empresas"
    )

    cnt_sin_asig = int(df_emp_orig["kam_id"].isin(cfg.valores_origen_sin_asignar).sum())
    df_emp_silver = df_emp_orig.copy()
    df_emp_silver["kam_valor_original"] = df_emp_silver["kam_id"]
    df_emp_silver["kam_id"] = df_emp_silver["kam_id"].apply(
        lambda v: homologar_kam_id(v, cfg)
    )
    cols_disp = [c for c in COLS_DESCRIPTIVAS_EMPRESA if c in df_emp_silver.columns]
    df_emp_silver = df_emp_silver[cols_disp]
    guardar_tabla_medallion(df_emp_silver, cfg.silver_dir, "dim_empresas")

    df_emp_scd2 = construir_dim_empresas_scd2(
        df_emp_silver, bronze["registros_duplicados"], cfg
    )
    guardar_tabla_medallion(df_emp_scd2, cfg.silver_dir, "dim_empresas_scd2")

    n_inc = int(df_emp_scd2["tiene_fechas_inconsistentes"].sum())
    n_sup = int(df_emp_scd2["tiene_intervalo_superpuesto"].sum())
    n_no_rec = int(
        (
            df_emp_scd2["clasificacion_historia_scd2"]
            == "HISTORIA_NO_RECONSTRUIBLE_SIN_FECHAS_EN_ORIGEN"
        ).sum()
    )
    bitacora.registrar_calidad(
        "dim_empresas",
        "kam_id",
        tipo_inc="CLAVE_FORANEA_NO_HOMOLOGADA",
        val_orig="Valores 'Sin asignar' y 'Sin asignar (cuenta ACTHO)'",
        val_corr=f"{cfg.kam_sin_asignar_id} (conservando kam_valor_original)",
        estado="CORREGIDO_HOMOLOGADO",
        cant=cnt_sin_asig,
    )
    bitacora.registrar_calidad(
        "dim_empresas_scd2",
        "fecha_inicio_vigencia / fecha_fin_vigencia",
        tipo_inc="VALIDACION_VIGENCIAS_E_HISTORIA_SCD2",
        val_orig=(
            f"Inconsistentes (inicio>fin): {n_inc} | "
            f"Intervalos superpuestos: {n_sup} | Sin fechas en CRM: {n_no_rec}"
        ),
        val_corr=(
            "Clasificados explícitamente en clasificacion_historia_scd2 "
            "sin inventar fechas"
        ),
        estado="CLASIFICADO_DOCUMENTADO",
        cant=n_inc + n_sup + n_no_rec,
    )
    bitacora.registrar_carga(
        "bronze/dim_empresas -> silver/dim_empresas (+scd2)",
        t0,
        leidos=len(df_emp_orig),
        proc=len(df_emp_silver),
        ins=len(df_emp_silver),
        act=cnt_sin_asig,
    )
    return df_emp_silver, df_emp_scd2


def _procesar_dim_personas_y_eventos(
    bronze: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construye dim_personas y dim_eventos en la capa Silver.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría activa.

    Returns:
        Tupla con (df_per_silver, df_ev_silver).

    """
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_per_orig = bronze["dim_personas"].copy()
    cols_m_per = [
        c
        for c in (
            "id_persona",
            "asistio_eventos_2026",
            "respondio_encuestas",
            "eventos_asistidos_2026",
            "encuestas_presenciales",
            "encuestas_virtuales",
            "fecha_primer_evento_2026",
            "fecha_ultimo_evento_2026",
        )
        if c in df_per_orig.columns
    ]
    guardar_tabla_medallion(
        df_per_orig[cols_m_per], cfg.audit_dir, "audit_metricas_origen_personas"
    )

    n_per_sin_emp = int(df_per_orig["id_empresa_principal"].isna().sum())
    df_per_silver = pd.DataFrame(
        {
            "id_persona": df_per_orig["id_persona"],
            "id_empresa_principal": df_per_orig["id_empresa_principal"],
            "estado_resolucion_empresa": np.where(
                df_per_orig["id_empresa_principal"].notna(),
                "ASOCIADA",
                "SIN_EMPRESA_ASOCIADA",
            ),
            "nivel_cargo": df_per_orig["nivel_cargo"],
            "ciudad": df_per_orig["ciudad"],
            "es_afiliado_principal_nuevo": df_per_orig[
                "es_afiliado_principal_nuevo"
            ].astype(bool),
            "fecha_afiliacion_nueva": df_per_orig["fecha_afiliacion_nueva"],
        }
    )
    guardar_tabla_medallion(df_per_silver, cfg.silver_dir, "dim_personas")
    bitacora.registrar_calidad(
        "dim_personas",
        "id_empresa_principal",
        tipo_inc="RELACION_OPCIONAL_NULA",
        val_orig=f"NaN ({n_per_sin_emp} personas sin empresa asociada)",
        val_corr="Se conserva NaN con estado_resolucion_empresa='SIN_EMPRESA_ASOCIADA'",
        estado="DOCUMENTADO_CONSERVADO",
        cant=n_per_sin_emp,
    )
    bitacora.registrar_carga(
        "bronze/dim_personas -> silver/dim_personas",
        t0,
        leidos=len(df_per_orig),
        proc=len(df_per_silver),
        ins=len(df_per_silver),
        act=0,
    )

    t1 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_ev_orig = bronze["dim_eventos"].copy()
    cols_ev = [
        c
        for c in (
            "id_evento",
            "archivo_csv",
            "fecha_evento",
            "fecha_inicio_evento",
            "fecha_fin_evento",
            "periodo_mes_iso",
            "nombre_evento",
            "linea_oferta_2027",
            "experiencia_detalle",
            "modalidad",
            "es_presencial",
            "tiene_asistentes_registrados",
        )
        if c in df_ev_orig.columns
    ]
    df_ev_silver = df_ev_orig[cols_ev].copy()
    guardar_tabla_medallion(df_ev_silver, cfg.silver_dir, "dim_eventos")
    bitacora.registrar_carga(
        "bronze/dim_eventos -> silver/dim_eventos",
        t1,
        leidos=len(df_ev_orig),
        proc=len(df_ev_silver),
        ins=len(df_ev_silver),
        act=0,
    )
    return df_per_silver, df_ev_silver


def _procesar_fact_asistencias(
    bronze: dict[str, pd.DataFrame],
    df_ev_silver: pd.DataFrame,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye fact_asistencias en Silver y concilia métricas de eventos en Audit.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.
        df_ev_silver: DataFrame de eventos en capa Silver.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría activa.

    Returns:
        DataFrame depurado de fact_asistencias.

    """
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_asist_orig = bronze["fact_asistencias"].copy()
    ev_mod_map = df_ev_silver.set_index("id_evento")["modalidad"].to_dict()
    n_sin_emp = int(df_asist_orig["id_empresa"].isna().sum())
    n_kam_hom = int(df_asist_orig["kam_id"].isin(cfg.valores_origen_sin_asignar).sum())

    df_asist_silver = df_asist_orig.copy()
    df_asist_silver["kam_valor_original"] = df_asist_silver["kam_id"]
    df_asist_silver["kam_id"] = df_asist_silver["kam_id"].apply(
        lambda v: homologar_kam_id(v, cfg)
    )
    df_asist_silver["tipo_asistencia"] = np.where(
        df_asist_silver["es_afiliado"].astype(bool),
        "Afiliado",
        "No Afiliado / Invitado",
    )
    df_asist_silver["modalidad_evento"] = df_asist_silver["id_evento"].map(ev_mod_map)
    df_asist_silver["estado_resolucion_identidad"] = np.where(
        df_asist_silver["id_empresa"].notna() & df_asist_silver["id_persona"].notna(),
        "IDENTIDAD_COMPLETA",
        "PENDIENTE_RESOLUCION_EMPRESA",
    )
    guardar_tabla_medallion(df_asist_silver, cfg.silver_dir, "fact_asistencias")

    bitacora.registrar_calidad(
        "fact_asistencias",
        "id_empresa",
        tipo_inc="IDENTIFICADOR_FALTANTE_EN_HECHO",
        val_orig=f"NaN ({n_sin_emp} asistencias sin empresa)",
        val_corr=(
            "Se conserva NaN con "
            "estado_resolucion_identidad='PENDIENTE_RESOLUCION_EMPRESA'"
        ),
        estado="DOCUMENTADO_CONSERVADO",
        cant=n_sin_emp,
    )
    bitacora.registrar_calidad(
        "fact_asistencias",
        "kam_id",
        tipo_inc="CLAVE_FORANEA_NO_HOMOLOGADA",
        val_orig="Valores sin asignar en fact_asistencias",
        val_corr=f"{cfg.kam_sin_asignar_id} (conservando kam_valor_original)",
        estado="CORREGIDO_HOMOLOGADO",
        cant=n_kam_hom,
    )
    bitacora.registrar_carga(
        "bronze/fact_asistencias -> silver/fact_asistencias",
        t0,
        leidos=len(df_asist_orig),
        proc=len(df_asist_silver),
        ins=len(df_asist_silver),
        act=n_kam_hom,
    )
    _guardar_audit_metricas_eventos(bronze["dim_eventos"], df_asist_silver, cfg)
    return df_asist_silver


def _guardar_audit_metricas_eventos(
    df_ev_orig: pd.DataFrame,
    df_asist_silver: pd.DataFrame,
    cfg: ConfiguracionETL,
) -> None:
    """Concilia las métricas de eventos reportadas en origen vs fact_asistencias.

    Args:
        df_ev_orig: DataFrame de eventos desde Bronze.
        df_asist_silver: DataFrame de asistencias en Silver.
        cfg: Configuración del pipeline ETL Medallion.

    """
    calc_ev = df_asist_silver.groupby("id_evento", as_index=False).agg(
        asistencias_calculadas_hechos=("id_asistencia", "count"),
        empresas_unicas_calculadas=("id_empresa", "nunique"),
        personas_unicas_calculadas=("id_persona", "nunique"),
    )
    cols_ev_audit = [
        c
        for c in (
            "id_evento",
            "archivo_csv",
            "nombre_evento",
            "total_asistentes_archivo",
            "empresas_unicas_archivo",
            "personas_unicas_archivo",
            "total_reportado_matriz_general",
        )
        if c in df_ev_orig.columns
    ]
    df_audit_ev = df_ev_orig[cols_ev_audit].merge(calc_ev, on="id_evento", how="left")
    for col in (
        "asistencias_calculadas_hechos",
        "empresas_unicas_calculadas",
        "personas_unicas_calculadas",
    ):
        df_audit_ev[col] = df_audit_ev[col].fillna(0).astype(int)
    if (
        "total_asistentes_archivo" in df_audit_ev.columns
        and "total_reportado_matriz_general" in df_audit_ev.columns
    ):
        df_audit_ev["diferencia_archivo_vs_matriz_general"] = (
            df_audit_ev["total_asistentes_archivo"]
            - df_audit_ev["total_reportado_matriz_general"]
        )
    guardar_tabla_medallion(df_audit_ev, cfg.audit_dir, "audit_metricas_origen_eventos")


def _estado_identidad_encuesta(row: pd.Series) -> str:
    """Clasifica el nivel de resolución de identidad de una respuesta de encuesta.

    Args:
        row: Serie con los campos id_persona e id_empresa.

    Returns:
        Estado de resolución de identidad de la encuesta.

    """
    tiene_p = pd.notna(row["id_persona"]) and str(row["id_persona"]).strip() != ""
    tiene_e = pd.notna(row["id_empresa"]) and str(row["id_empresa"]).strip() != ""
    if tiene_p and tiene_e:
        return "CORRESPONDENCIA_COMPLETA"
    if tiene_p and not tiene_e:
        return "SIN_CORRESPONDENCIA_EMPRESA"
    if not tiene_p and tiene_e:
        return "SIN_CORRESPONDENCIA_PERSONA"
    return "RESPUESTA_ANONIMA_SIN_CORRESPONDENCIA"


def _clasificar_expiracion_nula(row: pd.Series) -> str:
    """Clasifica la presencia o ausencia de fecha de expiración en movimientos CRM.

    Args:
        row: Serie de un movimiento CRM.

    Returns:
        Clasificación de la fecha de expiración.

    """
    val = row["fecha_expiracion_afiliacion"]
    if pd.notna(val) and str(val).strip() != "":
        return "CON_FECHA_EXPIRACION_REGISTRADA"
    if row["tipo_movimiento"] == "Trato en Estado":
        return "NO_REQUIERE_VENCIMIENTO_TRATO_PIPELINE"
    return "DATO_INCOMPLETO_EN_REPORTE_ALTA"


def _procesar_encuestas_y_movimientos(
    bronze: dict[str, pd.DataFrame],
    df_emp_silver: pd.DataFrame,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construye fact_encuestas_satisfaccion y fact_movimientos_crm en Silver.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.
        df_emp_silver: DataFrame depurado de empresas en Silver.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría activa.

    Returns:
        Tupla con (df_enc_silver, df_mov_silver).

    """
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_enc_orig = bronze["fact_encuestas_satisfaccion"].copy()
    n_sin_per = int(df_enc_orig["id_persona"].isna().sum())
    n_sin_emp = int(df_enc_orig["id_empresa"].isna().sum())

    df_enc_silver = df_enc_orig.copy()
    df_enc_silver.insert(
        3, "id_evento", pd.Series([pd.NA] * len(df_enc_silver), dtype="Int64")
    )
    df_enc_silver["estado_resolucion_identidad"] = df_enc_silver.apply(
        _estado_identidad_encuesta, axis=1
    )
    df_enc_silver["tipo_encuesta"] = "ENCUESTA_POST_EVENTO_SATISFACCION_1_5"
    df_enc_silver["pregunta_recomendacion_nps_0_10"] = pd.Series(
        [np.nan] * len(df_enc_silver), dtype="float64"
    )
    df_enc_silver["categoria_nps_0_10"] = "NO_DISPONIBLE_ESCALA_1_5"
    guardar_tabla_medallion(df_enc_silver, cfg.silver_dir, "fact_encuestas_satisfaccion")
    bitacora.registrar_calidad(
        "fact_encuestas_satisfaccion",
        "id_persona / id_empresa / id_evento",
        tipo_inc="SIN_ASOCIACION_EVENTO_Y_RESPUESTAS_ANONIMAS",
        val_orig=(
            f"Sin id_evento en fuente ({len(df_enc_silver)}), "
            f"sin id_persona ({n_sin_per}), sin id_empresa ({n_sin_emp})"
        ),
        val_corr=(
            "No se infiere evento; se conservan respuestas anónimas y se "
            "mantiene satisfacción 1-5 separada de NPS 0-10"
        ),
        estado="REGLA_NEGOCIO_APLICADA",
        cant=len(df_enc_silver),
    )
    bitacora.registrar_carga(
        "bronze/fact_encuestas_satisfaccion -> silver/fact_encuestas_satisfaccion",
        t0,
        leidos=len(df_enc_orig),
        proc=len(df_enc_silver),
        ins=len(df_enc_silver),
        act=0,
    )

    t1 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_mov_orig = bronze["fact_movimientos_crm"].copy()
    emp_estado_map: dict[Any, Any] = df_emp_silver.set_index("id_empresa")[
        "estado_membresia_detalle"
    ].to_dict()
    df_mov_silver = df_mov_orig.copy()
    df_mov_silver.insert(
        0,
        "id_movimiento",
        [f"MOV-{i:04d}" for i in range(1, len(df_mov_silver) + 1)],
    )
    df_mov_silver["kam_valor_original"] = df_mov_silver["kam_id"]
    df_mov_silver["kam_id"] = df_mov_silver["kam_id"].apply(
        lambda v: homologar_kam_id(v, cfg)
    )
    df_mov_silver["estado_afiliacion_empresa"] = (
        df_mov_silver["id_empresa"].map(emp_estado_map).fillna("Sin dato")
    )
    df_mov_silver["clasificacion_fecha_expiracion"] = df_mov_silver.apply(
        _clasificar_expiracion_nula, axis=1
    )
    guardar_tabla_medallion(df_mov_silver, cfg.silver_dir, "fact_movimientos_crm")
    bitacora.registrar_carga(
        "bronze/fact_movimientos_crm -> silver/fact_movimientos_crm",
        t1,
        leidos=len(df_mov_orig),
        proc=len(df_mov_silver),
        ins=len(df_mov_silver),
        act=len(df_mov_silver),
    )
    return df_enc_silver, df_mov_silver


def procesar_capa_silver(
    bronze: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> dict[str, pd.DataFrame]:
    """Ejecuta la construcción de todas las tablas de la capa Silver.

    Args:
        bronze: Diccionario de DataFrames validados en Bronze.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría activa.

    Returns:
        Diccionario con todos los DataFrames generados en la capa Silver.

    """
    df_kams = _procesar_dim_kams(bronze, cfg, bitacora)
    df_emp, df_emp_scd2 = _procesar_dim_empresas(bronze, cfg, bitacora)
    df_per, df_ev = _procesar_dim_personas_y_eventos(bronze, cfg, bitacora)
    df_asist = _procesar_fact_asistencias(bronze, df_ev, cfg, bitacora)
    df_enc, df_mov = _procesar_encuestas_y_movimientos(bronze, df_emp, cfg, bitacora)
    return {
        "dim_kams": df_kams,
        "dim_empresas": df_emp,
        "dim_empresas_scd2": df_emp_scd2,
        "dim_personas": df_per,
        "dim_eventos": df_ev,
        "fact_asistencias": df_asist,
        "fact_encuestas_satisfaccion": df_enc,
        "fact_movimientos_crm": df_mov,
    }
