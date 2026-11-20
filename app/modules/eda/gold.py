"""Agregaciones analíticas en capa Gold (Participación, Satisfacción y Retención)."""

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from app.modules.eda.audit import BitacoraAuditoria
from app.modules.eda.bronze import guardar_tabla_medallion
from app.modules.eda.config import ConfiguracionETL

COLS_CONTEO_PARTICIPACION: tuple[str, ...] = (
    "total_eventos",
    "total_asistencias",
    "personas_distintas_participantes",
    "asistencias_trimestre_calendario",
    "asistencias_trimestre_operativo",
    "asistencias_ventana_movil_90d_corte",
    "asistencias_ventana_movil_90d_ultimo_evento",
    "participacion_linea_anticipar",
    "participacion_linea_evento_grande",
    "participacion_linea_foro",
    "participacion_linea_pares",
    "participacion_modalidad_presencial",
    "participacion_modalidad_virtual",
    "participacion_modalidad_hibrido",
)


def _clasificar_recencia_part(row: pd.Series) -> str:
    """Clasifica el estado de recencia de participación de una empresa.

    Args:
        row: Serie con total_eventos y meses_sin_participacion.

    Returns:
        Categoría de recencia de participación.

    """
    if row["total_eventos"] == 0 or pd.isna(row["meses_sin_participacion"]):
        return "SIN_PARTICIPACION_REGISTRADA"
    meses = float(row["meses_sin_participacion"])
    if meses <= 1.0:
        return "PARTICIPACION_ULTIMO_MES"
    if meses <= 3.0:
        return "PARTICIPACION_ENTRE_1_Y_3_MESES"
    return "MAS_DE_3_MESES_SIN_PARTICIPAR"


def construir_agg_participacion_empresa(
    silver: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye y persiste agg_participacion_empresa en la capa Gold.

    Args:
        silver: Diccionario de DataFrames de la capa Silver.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría activa.

    Returns:
        DataFrame de participación agregada por empresa.

    """
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_asist_silver = silver["fact_asistencias"]
    df_ev_silver = silver["dim_eventos"]
    df_emp_silver = silver["dim_empresas"]
    fecha_corte_dt = pd.Timestamp(cfg.fecha_corte)

    df_asist_emp = df_asist_silver[df_asist_silver["id_empresa"].notna()].copy()
    df_asist_emp = df_asist_emp.merge(
        df_ev_silver[["id_evento", "linea_oferta_2027"]],
        on="id_evento",
        how="left",
    )
    df_asist_emp["_fecha_ev_dt"] = pd.to_datetime(
        df_asist_emp["fecha_evento"], errors="coerce"
    )

    ini_90d_corte = fecha_corte_dt - pd.Timedelta(days=cfg.ventana_movil_dias)
    max_fecha_ev = df_asist_emp["_fecha_ev_dt"].max()
    if pd.isna(max_fecha_ev):
        max_fecha_ev = fecha_corte_dt
    ini_90d_op = max_fecha_ev - pd.Timedelta(days=cfg.ventana_movil_dias)

    meses_cal = set(cfg.trimestre_calendario_meses)
    meses_op = set(cfg.trimestre_operativo_meses)

    agg_base = df_asist_emp.groupby("id_empresa", as_index=False).agg(
        total_eventos=("id_evento", "nunique"),
        total_asistencias=("id_asistencia", "count"),
        personas_distintas_participantes=("id_persona", "nunique"),
        ultima_fecha_participacion=("fecha_evento", "max"),
        primera_fecha_participacion=("fecha_evento", "min"),
        asistencias_trimestre_calendario=(
            "periodo_mes_iso",
            lambda s: int(s.isin(meses_cal).sum()),
        ),
        asistencias_trimestre_operativo=(
            "periodo_mes_iso",
            lambda s: int(s.isin(meses_op).sum()),
        ),
        asistencias_ventana_movil_90d_corte=(
            "_fecha_ev_dt",
            lambda s: int(
                s.between(ini_90d_corte, fecha_corte_dt, inclusive="both").sum()
            ),
        ),
        asistencias_ventana_movil_90d_ultimo_evento=(
            "_fecha_ev_dt",
            lambda s: int(s.between(ini_90d_op, max_fecha_ev, inclusive="both").sum()),
        ),
        participacion_linea_anticipar=(
            "linea_oferta_2027",
            lambda s: int((s == "Anticipar").sum()),
        ),
        participacion_linea_evento_grande=(
            "linea_oferta_2027",
            lambda s: int((s == "Evento grande").sum()),
        ),
        participacion_linea_foro=(
            "linea_oferta_2027",
            lambda s: int((s == "Foro").sum()),
        ),
        participacion_linea_pares=(
            "linea_oferta_2027",
            lambda s: int((s == "Pares").sum()),
        ),
        participacion_modalidad_presencial=(
            "modalidad_evento",
            lambda s: int((s == "Presencial").sum()),
        ),
        participacion_modalidad_virtual=(
            "modalidad_evento",
            lambda s: int((s == "Virtual").sum()),
        ),
        participacion_modalidad_hibrido=(
            "modalidad_evento",
            lambda s: int((s == "Híbrido").sum()),
        ),
    )

    cols_emp = ["id_empresa", "kam_id", "es_membresia_activa", "nivel_membresia"]
    agg_part = df_emp_silver[cols_emp].merge(agg_base, on="id_empresa", how="left")
    agg_part.insert(1, "periodo_analisis", f"{cfg.anio_analisis}-ANUAL")
    agg_part.insert(2, "fecha_corte_referencia", cfg.fecha_corte)
    agg_part.insert(3, "etiqueta_trimestre_calendario", cfg.trimestre_calendario_etiqueta)

    for col in COLS_CONTEO_PARTICIPACION:
        agg_part[col] = agg_part[col].fillna(0).astype(int)

    ult_dt = pd.to_datetime(agg_part["ultima_fecha_participacion"], errors="coerce")
    dias_inact = (fecha_corte_dt - ult_dt).dt.days
    agg_part["dias_sin_participacion"] = dias_inact
    agg_part["meses_sin_participacion"] = (dias_inact / cfg.dias_por_mes_estandar).round(
        2
    )
    agg_part["estado_recencia_participacion"] = agg_part.apply(
        _clasificar_recencia_part, axis=1
    )

    guardar_tabla_medallion(agg_part, cfg.gold_dir, "agg_participacion_empresa")
    bitacora.registrar_carga(
        "silver -> gold/agg_participacion_empresa",
        t0,
        leidos=len(df_asist_silver),
        proc=len(agg_part),
        ins=len(agg_part),
        act=0,
    )
    return agg_part


def construir_agg_satisfaccion_encuestas(
    df_enc_silver: pd.DataFrame,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye y persiste agg_satisfaccion_encuestas en la capa Gold.

    Args:
        df_enc_silver: DataFrame de encuestas desde Silver.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría activa.

    Returns:
        DataFrame de satisfacción agregada por modalidad y periodo mensual.

    """
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    agg_sat = (
        df_enc_silver.groupby(
            ["modalidad_encuesta", "periodo_mes_iso"],
            dropna=False,
            as_index=False,
        )
        .agg(
            total_respuestas=("id_respuesta", "count"),
            respuestas_con_empresa_resuelta=(
                "id_empresa",
                lambda s: int(s.notna().sum()),
            ),
            respuestas_sin_empresa=("id_empresa", lambda s: int(s.isna().sum())),
            respuestas_anonimas_sin_persona=(
                "id_persona",
                lambda s: int(s.isna().sum()),
            ),
            promedio_satisfaccion_general_1_5=("promedio_satisfaccion", "mean"),
            promedio_locacion_plataforma_1_5=(
                "calif_locacion_o_plataforma",
                "mean",
            ),
            promedio_convocatoria_1_5=("calif_convocatoria_publicidad", "mean"),
            promedio_conferencistas_1_5=("calif_conferencistas", "mean"),
            promedio_relevancia_temas_1_5=("calif_relevancia_temas", "mean"),
            calificaciones_altas_475_a_500=(
                "promedio_satisfaccion",
                lambda s: int((s >= 4.75).sum()),
            ),
            calificaciones_medias_375_a_474=(
                "promedio_satisfaccion",
                lambda s: int(((s >= 3.75) & (s < 4.75)).sum()),
            ),
            calificaciones_bajas_menores_375=(
                "promedio_satisfaccion",
                lambda s: int((s < 3.75).sum()),
            ),
            promotores_nps_0_10=(
                "pregunta_recomendacion_nps_0_10",
                lambda s: int((s >= 9).sum()) if s.notna().any() else pd.NA,
            ),
            pasivos_nps_0_10=(
                "pregunta_recomendacion_nps_0_10",
                lambda s: (int(s.between(7, 8).sum()) if s.notna().any() else pd.NA),
            ),
            detractores_nps_0_10=(
                "pregunta_recomendacion_nps_0_10",
                lambda s: int((s <= 6).sum()) if s.notna().any() else pd.NA,
            ),
        )
        .sort_values(["modalidad_encuesta", "periodo_mes_iso"])
        .reset_index(drop=True)
    )
    for col_m in (
        "promedio_satisfaccion_general_1_5",
        "promedio_locacion_plataforma_1_5",
        "promedio_convocatoria_1_5",
        "promedio_conferencistas_1_5",
        "promedio_relevancia_temas_1_5",
    ):
        agg_sat[col_m] = agg_sat[col_m].round(2)

    def _calcular_nps_fila(row: pd.Series) -> float:
        prom = row["promotores_nps_0_10"]
        pas = row["pasivos_nps_0_10"]
        det = row["detractores_nps_0_10"]
        if pd.isna(prom) or pd.isna(pas) or pd.isna(det):
            return float("nan")
        total_nps = int(prom) + int(pas) + int(det)
        if total_nps <= 0:
            return float("nan")
        return round(((int(prom) - int(det)) / total_nps) * 100.0, 2)

    agg_sat["nps_oficial_0_10"] = agg_sat.apply(_calcular_nps_fila, axis=1)
    agg_sat["estado_calculo_nps"] = np.where(
        agg_sat["nps_oficial_0_10"].notna(),
        "CALCULADO_ENCUESTA_RECOMENDACION_0_10",
        "NO_CALCULABLE_SIN_PREGUNTA_RECOMENDACION_0_10",
    )
    agg_sat["asociacion_evento_origen"] = "NO_DISPONIBLE_EN_FUENTE_ENCUESTAS"
    guardar_tabla_medallion(agg_sat, cfg.gold_dir, "agg_satisfaccion_encuestas")
    bitacora.registrar_carga(
        "silver -> gold/agg_satisfaccion_encuestas",
        t0,
        leidos=len(df_enc_silver),
        proc=len(agg_sat),
        ins=len(agg_sat),
        act=0,
    )
    return agg_sat


def _preparar_base_retencion(
    bronze: dict[str, pd.DataFrame],
    silver: dict[str, pd.DataFrame],
    agg_part_empresa: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida la tabla base de retención cruzando dimensiones, SCD2 y hechos.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.
        silver: Diccionario de DataFrames de la capa Silver.
        agg_part_empresa: DataFrame de participación por empresa.

    Returns:
        DataFrame consolidado previo al cálculo del semáforo de riesgo.

    """
    df_emp_silver = silver["dim_empresas"]
    df_emp_scd2 = silver["dim_empresas_scd2"]
    df_enc_silver = silver["fact_encuestas_satisfaccion"]
    df_mov_silver = silver["fact_movimientos_crm"]

    reno_por_emp = (
        df_mov_silver[df_mov_silver["es_renovacion"].astype(bool)]
        .groupby("id_empresa", as_index=False)
        .agg(renovaciones_registradas_2026=("id_movimiento", "count"))
    )

    estados_inactivos = {"Cancelado", "Expirado", "Inactivo"}
    hist_inact_scd2 = (
        df_emp_scd2[
            (~df_emp_scd2["es_registro_actual"])
            & (df_emp_scd2["estado_membresia_detalle"].isin(estados_inactivos))
        ]
        .groupby("id_empresa", as_index=False)
        .agg(estados_inactivos_historicos_scd2=("sk_empresa_scd2", "count"))
    )
    total_inact_scd2 = (
        df_emp_scd2[df_emp_scd2["estado_membresia_detalle"].isin(estados_inactivos)]
        .groupby("id_empresa", as_index=False)
        .agg(numero_retiros_historicos=("sk_empresa_scd2", "count"))
    )

    sat_emp = (
        df_enc_silver[df_enc_silver["id_empresa"].notna()]
        .sort_values("fecha_encuesta")
        .groupby("id_empresa", as_index=False)
        .agg(
            respuestas_encuestas_total=("id_respuesta", "count"),
            satisfaccion_promedio_1_5=("promedio_satisfaccion", "mean"),
            satisfaccion_reciente_1_5=("promedio_satisfaccion", "last"),
            fecha_ultima_encuesta=("fecha_encuesta", "max"),
        )
    )
    sat_emp["satisfaccion_promedio_1_5"] = sat_emp["satisfaccion_promedio_1_5"].round(2)

    cols_orig_ind = [
        c
        for c in (
            "id_empresa",
            "en_seguimiento_kam",
            "asistio_segun_kam",
            "eventos_reportados_kam",
        )
        if c in bronze["dim_empresas"].columns
    ]
    df_orig_ind = bronze["dim_empresas"][cols_orig_ind].copy()

    cols_emp_base = [
        "id_empresa",
        "kam_id",
        "en_crm_afiliados",
        "es_empresa_activa",
        "es_membresia_activa",
        "estado_membresia_detalle",
        "segmento_membresia",
        "nivel_membresia",
        "fecha_afiliacion",
        "fecha_expiracion",
        "fecha_ultima_actividad",
    ]
    cols_part_merge = [
        "id_empresa",
        "total_eventos",
        "total_asistencias",
        "personas_distintas_participantes",
        "asistencias_trimestre_calendario",
        "asistencias_trimestre_operativo",
        "asistencias_ventana_movil_90d_corte",
        "asistencias_ventana_movil_90d_ultimo_evento",
        "ultima_fecha_participacion",
        "dias_sin_participacion",
        "meses_sin_participacion",
        "estado_recencia_participacion",
    ]
    agg_ret = (
        df_emp_silver[cols_emp_base]
        .merge(reno_por_emp, on="id_empresa", how="left")
        .merge(hist_inact_scd2, on="id_empresa", how="left")
        .merge(total_inact_scd2, on="id_empresa", how="left")
        .merge(agg_part_empresa[cols_part_merge], on="id_empresa", how="left")
        .merge(sat_emp, on="id_empresa", how="left")
        .merge(df_orig_ind, on="id_empresa", how="left")
    )
    for col in (
        "renovaciones_registradas_2026",
        "estados_inactivos_historicos_scd2",
        "numero_retiros_historicos",
        "respuestas_encuestas_total",
    ):
        agg_ret[col] = agg_ret[col].fillna(0).astype(int)

    agg_ret["es_retiro_definitivo_actual"] = agg_ret["en_crm_afiliados"].astype(bool) & (
        agg_ret["estado_membresia_detalle"].isin(estados_inactivos)
    )

    cols_fechas = [
        "fecha_ultima_actividad",
        "ultima_fecha_participacion",
        "fecha_ultima_encuesta",
    ]
    agg_ret["fecha_ultima_interaccion_global"] = (
        agg_ret[cols_fechas]
        .astype(str)
        .replace({"nan": "", "None": "", "<NA>": ""})
        .max(axis=1)
        .replace("", np.nan)
    )
    return agg_ret


def _aplicar_semaforo_riesgo(
    agg_retencion: pd.DataFrame, cfg: ConfiguracionETL
) -> pd.DataFrame:
    """Calcula vencimientos, alertas heurísticas y el semáforo de riesgo en Gold.

    Args:
        agg_retencion: DataFrame base de retención por empresa.
        cfg: Configuración del pipeline ETL Medallion.

    Returns:
        DataFrame de retención enriquecido con el semáforo heurístico.

    """
    fecha_corte_dt = pd.Timestamp(cfg.fecha_corte)
    exp_dt = pd.to_datetime(agg_retencion["fecha_expiracion"], errors="coerce")
    agg_retencion["dias_para_expiracion"] = (exp_dt - fecha_corte_dt).dt.days

    umbrales = cfg.reglas_semaforo.get("umbrales", {})
    pesos = cfg.reglas_semaforo.get("pesos", {})
    d_inm = int(umbrales.get("dias_vencimiento_inmediato", 30))
    d_med = int(umbrales.get("dias_vencimiento_medio", 60))
    d_prox = int(umbrales.get("dias_vencimiento_proximo", 90))
    min_ev = int(umbrales.get("min_eventos_participacion_activa", 1))
    sat_max_det = float(umbrales.get("satisfaccion_detractor_max_1_5", 3.75))
    max_mono = int(umbrales.get("max_personas_monocontacto", 1))
    pts_rojo = int(umbrales.get("puntaje_minimo_rojo_alto", 4))
    pts_amar = int(umbrales.get("puntaje_minimo_amarillo_medio", 2))

    agg_retencion["es_membresia_vencida"] = agg_retencion[
        "dias_para_expiracion"
    ].notna() & (agg_retencion["dias_para_expiracion"] < 0)
    agg_retencion["es_proximo_vencimiento_30d"] = agg_retencion[
        "dias_para_expiracion"
    ].between(0, d_inm, inclusive="both")
    agg_retencion["es_proximo_vencimiento_60d"] = agg_retencion[
        "dias_para_expiracion"
    ].between(0, d_med, inclusive="both")
    agg_retencion["es_proximo_vencimiento_90d"] = agg_retencion[
        "dias_para_expiracion"
    ].between(0, d_prox, inclusive="both")

    def clasificar_vencimiento(dias: Any) -> str:
        if pd.isna(dias):
            return "SIN_FECHA_EXPIRACION"
        val_d = float(dias)
        if val_d < 0:
            return "VENCIDA_FECHA_PASADA"
        if val_d <= d_inm:
            return "PROXIMA_A_VENCER_0_30_DIAS"
        if val_d <= d_med:
            return "PROXIMA_A_VENCER_31_60_DIAS"
        if val_d <= d_prox:
            return "PROXIMA_A_VENCER_61_90_DIAS"
        return "VIGENTE_MAS_DE_90_DIAS"

    agg_retencion["estado_vigencia_expiracion"] = agg_retencion[
        "dias_para_expiracion"
    ].apply(clasificar_vencimiento)

    agg_retencion["alerta_membresia_vencida"] = agg_retencion["es_membresia_vencida"]
    agg_retencion["alerta_proximo_vencimiento_90d"] = agg_retencion[
        "es_proximo_vencimiento_90d"
    ]
    agg_retencion["alerta_baja_participacion"] = agg_retencion["total_eventos"] < min_ev
    agg_retencion["alerta_baja_satisfaccion"] = agg_retencion[
        "satisfaccion_reciente_1_5"
    ].notna() & (agg_retencion["satisfaccion_reciente_1_5"] < sat_max_det)
    agg_retencion["alerta_monocontacto"] = (agg_retencion["total_eventos"] >= min_ev) & (
        agg_retencion["personas_distintas_participantes"] <= max_mono
    )

    agg_retencion["puntaje_heuristico_riesgo"] = (
        np.where(
            agg_retencion["alerta_membresia_vencida"],
            int(pesos.get("membresia_vencida", 2)),
            0,
        )
        + np.where(
            agg_retencion["alerta_proximo_vencimiento_90d"],
            int(pesos.get("proximo_vencimiento_90d", 2)),
            0,
        )
        + np.where(
            agg_retencion["alerta_baja_participacion"],
            int(pesos.get("baja_participacion_cero_eventos", 2)),
            0,
        )
        + np.where(
            agg_retencion["alerta_baja_satisfaccion"],
            int(pesos.get("baja_satisfaccion_menor_3_75", 2)),
            0,
        )
        + np.where(
            agg_retencion["alerta_monocontacto"],
            int(pesos.get("monocontacto_una_persona", 1)),
            0,
        )
    )

    def evaluar_semaforo(row: pd.Series) -> str:
        if not row["es_membresia_activa"]:
            return "NO_APLICA_INACTIVO_O_PROSPECTO"
        pts = int(row["puntaje_heuristico_riesgo"])
        if pts >= pts_rojo:
            return "ROJO_RIESGO_ALTO"
        if pts >= pts_amar:
            return "AMARILLO_RIESGO_MEDIO"
        return "VERDE_RIESGO_BAJO"

    agg_retencion["semaforo_riesgo_renovacion"] = agg_retencion.apply(
        evaluar_semaforo, axis=1
    )
    agg_retencion["tipo_metodologia_riesgo"] = str(
        cfg.reglas_semaforo.get(
            "tipo_metodologia", "REGLA_HEURISTICA_NEGOCIO_NO_PREDICTIVA"
        )
    )
    return agg_retencion


def construir_agg_retencion_empresa(
    bronze: dict[str, pd.DataFrame],
    silver: dict[str, pd.DataFrame],
    agg_part_empresa: pd.DataFrame,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye y persiste agg_retencion_empresa en la capa Gold.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.
        silver: Diccionario de DataFrames de la capa Silver.
        agg_part_empresa: DataFrame de participación agregada por empresa.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría activa.

    Returns:
        DataFrame de retención y riesgo de renovación por empresa.

    """
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    agg_retencion = _preparar_base_retencion(bronze, silver, agg_part_empresa)
    agg_retencion = _aplicar_semaforo_riesgo(agg_retencion, cfg)
    guardar_tabla_medallion(agg_retencion, cfg.gold_dir, "agg_retencion_empresa")
    bitacora.registrar_carga(
        "silver -> gold/agg_retencion_empresa",
        t0,
        leidos=len(silver["dim_empresas"]),
        proc=len(agg_retencion),
        ins=len(agg_retencion),
        act=0,
    )
    return agg_retencion
