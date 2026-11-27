"""Construcción del Esquema Estrella Analítico de la capa Gold (6 tablas)."""

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from app.modules.eda.audit import BitacoraAuditoria
from app.modules.eda.bronze import guardar_tabla_medallion
from app.modules.eda.config import ConfiguracionETL
from app.modules.eda.gold_segmentos import construir_mart_segmentos_comunicaciones
from app.modules.eda.gold_temas import (
    clasificar_tema_nlp,
    inicializar_columnas_ml_reservadas,
)

TABLAS_LEGADO_GOLD: tuple[str, ...] = (
    "agg_satisfaccion_evento",
    "agg_participacion_empresa",
    "agg_participacion_eventos",
    "agg_satisfaccion_encuestas",
    "agg_retencion_empresa",
    "agg_segmentos_comunicaciones",
)

COLS_EMPRESA_360: list[str] = [
    "id_empresa",
    "tipo_relacion_actho",
    "kam_id",
    "responsable_kam",
    "kam_con_seguimiento",
    "id_membresia_actual",
    "estado_membresia_detalle",
    "es_membresia_activa",
    "segmento_membresia",
    "nivel_membresia",
    "sector_economico",
    "subsector_economico",
    "tamano_empresa",
    "rango_empleados",
    "porcentaje_mujeres_num",
    "nombre_ciudad",
    "nombre_departamento",
    "nombre_pais",
    "fecha_miembro_desde",
    "fecha_afiliacion_actual",
    "fecha_inicio_vigencia",
    "fecha_fin_vigencia",
    "dias_para_expiracion",
    "tramo_vencimiento",
    "total_ciclos_membresia",
    "total_eventos_anio",
    "total_asistencias_anio",
    "personas_distintas_anio",
    "asistencias_ultimo_trimestre",
    "dias_sin_participacion",
    "total_encuestas_respondidas",
    "satisfaccion_promedio_1_5",
    "satisfaccion_reciente_1_5",
    "nps_reciente_0_10",
    "alerta_vencimiento_90d",
    "alerta_sin_participacion_trimestre",
    "alerta_baja_satisfaccion",
    "alerta_monocontacto",
    "puntaje_riesgo_heuristico",
    "probabilidad_churn_ml",
    "semaforo_riesgo_renovacion",
    "score_fidelidad_ml_0_100",
    "arquetipo_fidelidad_ml",
    "score_conversion_lead_ml_0_100",
    "linea_2027_mayor_participacion",
    "linea_2027_recomendada_ml",
    "prob_asistencia_prox_evento_ml",
]


def limpiar_archivos_legado_gold(cfg: ConfiguracionETL) -> None:
    """Elimina tablas Gold antiguas pre-agregadas que fueron reemplazadas."""
    for nombre in TABLAS_LEGADO_GOLD:
        for ext in ("csv", "parquet"):
            ruta = cfg.gold_dir / f"{nombre}.{ext}"
            if ruta.exists():
                ruta.unlink()


def _derivar_periodo_y_trimestre(serie_fecha: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Calcula periodo_mes_iso (YYYY-MM) y trimestre_iso (YYYY-Qn) desde fechas ISO."""
    dt = pd.to_datetime(serie_fecha, errors="coerce")
    periodo = dt.dt.strftime("%Y-%m").fillna("SIN_FECHA")
    trimestre = np.where(
        dt.isna(),
        "SIN_FECHA",
        dt.dt.year.astype("Int64").astype(str)
        + "-Q"
        + dt.dt.quarter.astype("Int64").astype(str),
    )
    return periodo, pd.Series(trimestre, index=serie_fecha.index)


def _construir_mapa_geografico_completo(
    silver: dict[str, pd.DataFrame],
) -> dict[int, tuple[str, str, str]]:
    """Construye un mapa rápido id_ciudad -> (ciudad, departamento, pais)."""
    df_c = silver["dim_ciudad"]
    if df_c.empty:
        return {}
    geo_join = df_c.merge(
        silver["dim_departamento"], on="id_departamento", how="left"
    ).merge(silver["dim_pais"], on="id_pais", how="left")
    return {
        int(r["id_ciudad"]): (
            str(r["nombre_ciudad"]),
            str(r["nombre_departamento"]),
            str(r["nombre_pais"]),
        )
        for _, r in geo_join.iterrows()
    }


def construir_fact_asistencias_bi(
    silver: dict[str, pd.DataFrame],
    mapa_geo: dict[int, tuple[str, str, str]],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye gold_fact_asistencias_bi con atributos de evento y ciudad resueltos."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_asi = silver["fact_asistencias"].copy()
    df_ev = silver["dim_eventos"][
        ["id_evento", "fecha_inicio_evento", "linea_oferta_2027", "modalidad"]
    ].copy()
    df_asi["id_evento"] = df_asi["id_evento"].astype(int)
    df_ev["id_evento"] = df_ev["id_evento"].astype(int)

    merged = df_asi.merge(df_ev, on="id_evento", how="left")
    periodo, trimestre = _derivar_periodo_y_trimestre(merged["fecha_inicio_evento"])
    ciudades_nom = [
        mapa_geo[int(cid)][0] if pd.notna(cid) and int(cid) in mapa_geo else None
        for cid in merged["id_ciudad_asistente"]
    ]

    df_out = pd.DataFrame(
        {
            "id_asistencia": merged["id_asistencia"],
            "id_evento": merged["id_evento"].astype(int),
            "id_empresa": merged["id_empresa"],
            "id_persona": merged["id_persona"],
            "id_vinculo": merged["id_vinculo"].astype("Int64"),
            "kam_id_asistencia": merged["kam_id"],
            "fecha_inicio_evento": merged["fecha_inicio_evento"],
            "periodo_mes_iso": periodo,
            "trimestre_iso": trimestre,
            "linea_oferta_2027": merged["linea_oferta_2027"],
            "modalidad": merged["modalidad"],
            "tipo_asistencia": merged["tipo_asistencia"],
            "nivel_cargo_evento": merged["nivel_cargo_evento"],
            "nombre_ciudad_asistente": ciudades_nom,
            "cantidad_inscritos_prov": merged["cantidad_inscritos"].astype("Int64"),
            "tiene_costo": merged["tiene_costo"],
            "autoriza_tratamiento_datos": merged["autoriza_tratamiento_datos"],
        }
    )
    guardar_tabla_medallion(df_out, cfg.gold_dir, "fact_asistencias_bi")
    bitacora.registrar_carga(
        "silver -> gold/fact_asistencias_bi",
        t0,
        leidos=len(df_asi),
        proc=len(df_out),
        ins=len(df_out),
        act=0,
    )
    return df_out


def construir_fact_encuestas_bi(
    df_enc_silver: pd.DataFrame,
    mapa_geo: dict[int, tuple[str, str, str]],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye gold_fact_encuestas_bi separando Likert 1-5 de NPS 0-10 y NLP."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_enc = df_enc_silver.copy()
    cols_likert = [
        "calif_locacion_o_plataforma",
        "calif_convocatoria_publicidad",
        "calif_conferencistas",
        "calif_relevancia_temas",
    ]
    mat_likert = (
        df_enc[cols_likert].apply(pd.to_numeric, errors="coerce").astype("float64")
    )
    prom_fila = mat_likert.mean(axis=1).round(2)
    niv_sat = [
        (
            None
            if pd.isna(v)
            else ("ALTA" if v >= 4.5 else ("MEDIA" if v >= 3.75 else "BAJA"))
        )
        for v in prom_fila
    ]

    nps_num = pd.to_numeric(
        df_enc["pregunta_recomendacion_nps_0_10"], errors="coerce"
    ).astype("float64")
    cat_nps = [
        (
            None
            if pd.isna(v)
            else ("PROMOTOR" if v >= 9 else ("PASIVO" if v >= 7 else "DETRACTOR"))
        )
        for v in nps_num
    ]
    periodo, trimestre = _derivar_periodo_y_trimestre(df_enc["fecha_encuesta"])
    ciudades_enc = [
        mapa_geo[int(cid)][0] if pd.notna(cid) and int(cid) in mapa_geo else None
        for cid in df_enc["id_ciudad_encuesta"]
    ]

    df_out = pd.DataFrame(
        {
            "id_respuesta": df_enc["id_respuesta"],
            "id_evento": pd.to_numeric(df_enc["id_evento"], errors="coerce").astype(
                "Int64"
            ),
            "id_empresa": df_enc["id_empresa"],
            "id_persona": df_enc["id_persona"],
            "fecha_encuesta": df_enc["fecha_encuesta"],
            "periodo_mes_iso": periodo,
            "trimestre_iso": trimestre,
            "tipo_encuesta": df_enc["tipo_encuesta"].fillna("POST_EVENTO"),
            "modalidad_encuesta": df_enc["modalidad_encuesta"].fillna("Virtual"),
            "nombre_ciudad_encuesta": ciudades_enc,
            "calif_locacion_o_plataforma": mat_likert[
                "calif_locacion_o_plataforma"
            ].astype("Int64"),
            "calif_convocatoria_publicidad": mat_likert[
                "calif_convocatoria_publicidad"
            ].astype("Int64"),
            "calif_conferencistas": mat_likert["calif_conferencistas"].astype("Int64"),
            "calif_relevancia_temas": mat_likert["calif_relevancia_temas"].astype(
                "Int64"
            ),
            "promedio_respuesta_1_5": prom_fila,
            "nivel_satisfaccion_1_5": niv_sat,
            "pregunta_recomendacion_nps_0_10": nps_num.round().astype("Int64"),
            "categoria_nps_0_10": cat_nps,
            "temarios_sugeridos": df_enc["temarios_sugeridos"],
            "categoria_tema_nlp": df_enc["temarios_sugeridos"].apply(clasificar_tema_nlp),
            "desea_recibir_actualizaciones": df_enc["desea_recibir_actualizaciones"],
        }
    )
    guardar_tabla_medallion(df_out, cfg.gold_dir, "fact_encuestas_bi")
    bitacora.registrar_carga(
        "silver -> gold/fact_encuestas_bi",
        t0,
        leidos=len(df_enc),
        proc=len(df_out),
        ins=len(df_out),
        act=0,
    )
    return df_out


def _clasificar_tramo_vencimiento(
    dias: Any, tiene_mem: bool, cfg: ConfiguracionETL
) -> str:
    """Clasifica el tramo temporal de vencimiento de una empresa."""
    if not tiene_mem or pd.isna(dias):
        return "SIN_MEMBRESIA"
    umbrales = cfg.reglas_semaforo.get("umbrales", {})
    val = float(dias)
    if val < 0:
        return "VENCIDA"
    if val <= int(umbrales.get("dias_vencimiento_inmediato", 30)):
        return "0_30D"
    if val <= int(umbrales.get("dias_vencimiento_medio", 60)):
        return "31_60D"
    if val <= int(umbrales.get("dias_vencimiento_proximo", 90)):
        return "61_90D"
    return "MAS_90D"


def _resumir_asistencias_y_encuestas_por_empresa(
    df_asist_bi: pd.DataFrame,
    df_enc_bi: pd.DataFrame,
    meses_op: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calcula métricas agregadas de participación y satisfacción por id_empresa."""
    sub_asi = df_asist_bi[df_asist_bi["id_empresa"].notna()]
    if not sub_asi.empty:
        lin_top = (
            sub_asi.groupby(["id_empresa", "linea_oferta_2027"])
            .size()
            .reset_index(name="cnt")
            .sort_values(["id_empresa", "cnt"], ascending=[True, False])
            .drop_duplicates(subset=["id_empresa"], keep="first")
            .set_index("id_empresa")["linea_oferta_2027"]
            .to_dict()
        )
        agg_asi = sub_asi.groupby("id_empresa", as_index=False).agg(
            total_eventos_anio=("id_evento", "nunique"),
            total_asistencias_anio=("id_asistencia", "count"),
            personas_distintas_anio=("id_persona", "nunique"),
            asistencias_ultimo_trimestre=(
                "periodo_mes_iso",
                lambda s: int(s.isin(meses_op).sum()),
            ),
            ultima_fecha_asist=("fecha_inicio_evento", "max"),
        )
        agg_asi["linea_2027_mayor_participacion"] = agg_asi["id_empresa"].map(lin_top)
    else:
        agg_asi = pd.DataFrame(
            columns=[
                "id_empresa",
                "total_eventos_anio",
                "total_asistencias_anio",
                "personas_distintas_anio",
                "asistencias_ultimo_trimestre",
                "ultima_fecha_asist",
                "linea_2027_mayor_participacion",
            ]
        )

    sub_enc = df_enc_bi[df_enc_bi["id_empresa"].notna()].sort_values("fecha_encuesta")
    if not sub_enc.empty:
        agg_enc = sub_enc.groupby("id_empresa", as_index=False).agg(
            total_encuestas_respondidas=("id_respuesta", "count"),
            satisfaccion_promedio_1_5=("promedio_respuesta_1_5", "mean"),
            satisfaccion_reciente_1_5=("promedio_respuesta_1_5", "last"),
            nps_reciente_0_10=("pregunta_recomendacion_nps_0_10", "last"),
        )
        agg_enc["satisfaccion_promedio_1_5"] = agg_enc["satisfaccion_promedio_1_5"].round(
            2
        )
    else:
        agg_enc = pd.DataFrame(
            columns=[
                "id_empresa",
                "total_encuestas_respondidas",
                "satisfaccion_promedio_1_5",
                "satisfaccion_reciente_1_5",
                "nps_reciente_0_10",
            ]
        )
    return agg_asi, agg_enc


def _aplicar_alertas_y_semaforo_hibrido(
    base: pd.DataFrame,
    cfg: ConfiguracionETL,
) -> pd.DataFrame:
    """Calcula vencimientos, alertas, columnas ML reservadas y semáforo de riesgo."""
    fecha_corte_dt = pd.Timestamp(cfg.fecha_corte)
    tiene_mem = base["id_membresia_actual"].notna()
    base["dias_para_expiracion"] = (
        pd.to_datetime(base["fecha_fin_vigencia"], errors="coerce") - fecha_corte_dt
    ).dt.days
    base["tramo_vencimiento"] = [
        _clasificar_tramo_vencimiento(d, bool(tm), cfg)
        for d, tm in zip(base["dias_para_expiracion"], tiene_mem)
    ]
    base["dias_sin_participacion"] = (
        fecha_corte_dt - pd.to_datetime(base["ultima_fecha_asist"], errors="coerce")
    ).dt.days

    umbrales = cfg.reglas_semaforo.get("umbrales", {})
    pesos = cfg.reglas_semaforo.get("pesos", {})
    sat_min = float(umbrales.get("satisfaccion_detractor_max_1_5", 3.75))

    base["alerta_vencimiento_90d"] = base["tramo_vencimiento"].isin(
        {"VENCIDA", "0_30D", "31_60D", "61_90D"}
    )
    base["alerta_sin_participacion_trimestre"] = base["asistencias_ultimo_trimestre"] == 0
    sat_rec_f = pd.to_numeric(base["satisfaccion_reciente_1_5"], errors="coerce")
    base["alerta_baja_satisfaccion"] = sat_rec_f.notna() & (sat_rec_f < sat_min)
    base["alerta_monocontacto"] = (base["total_eventos_anio"] >= 1) & (
        base["personas_distintas_anio"] <= 1
    )

    pts_bruto = (
        np.where(
            base["tramo_vencimiento"] == "VENCIDA",
            int(pesos.get("membresia_vencida", 2)),
            0,
        )
        + np.where(
            base["tramo_vencimiento"].isin({"0_30D", "31_60D", "61_90D"}),
            int(pesos.get("proximo_vencimiento_90d", 2)),
            0,
        )
        + np.where(
            base["total_eventos_anio"] == 0,
            int(pesos.get("baja_participacion_cero_eventos", 2)),
            np.where(base["alerta_sin_participacion_trimestre"], 1, 0),
        )
        + np.where(
            base["alerta_baja_satisfaccion"],
            int(pesos.get("baja_satisfaccion_menor_3_75", 2)),
            0,
        )
        + np.where(
            base["alerta_monocontacto"],
            int(pesos.get("monocontacto_una_persona", 1)),
            0,
        )
    )
    es_act = base["tipo_relacion_actho"] == "AFILIADO_ACTIVO"
    base["puntaje_riesgo_heuristico"] = pd.Series(
        [int(p) if act else pd.NA for act, p in zip(es_act, pts_bruto)],
        index=base.index,
        dtype="Int64",
    )

    base = inicializar_columnas_ml_reservadas(base)
    pts_rojo = int(umbrales.get("puntaje_minimo_rojo_alto", 4))
    pts_amar = int(umbrales.get("puntaje_minimo_amarillo_medio", 2))

    pts_num = base["puntaje_riesgo_heuristico"].fillna(0).astype(float)
    prob_num = base["probabilidad_churn_ml"].fillna(0.0).astype(float)
    base["semaforo_riesgo_renovacion"] = np.where(
        ~es_act,
        "NO_APLICA",
        np.where(
            (pts_num >= pts_rojo) | (prob_num >= 0.65),
            "ROJO",
            np.where((pts_num >= pts_amar) | (prob_num >= 0.35), "AMARILLO", "VERDE"),
        ),
    )
    base["nps_reciente_0_10"] = pd.to_numeric(
        base["nps_reciente_0_10"], errors="coerce"
    ).astype("Int64")
    return base


def construir_dim_empresa_360(
    silver: dict[str, pd.DataFrame],
    df_asist_bi: pd.DataFrame,
    df_enc_bi: pd.DataFrame,
    mapa_geo: dict[int, tuple[str, str, str]],
    *,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye gold_dim_empresa_360 integrando membresías, uso, riesgo y ML."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_emp = silver["dim_empresas"].copy()
    mem_full = silver["membresias"].merge(
        silver["dim_catalogo_membresia"], on="id_cat_membresia", how="left"
    )
    ciclos_cnt = (
        mem_full.groupby("id_empresa", as_index=False).agg(
            total_ciclos_membresia=("id_membresia", "count")
        )
        if not mem_full.empty
        else pd.DataFrame(columns=["id_empresa", "total_ciclos_membresia"])
    )
    ult_mem = (
        mem_full.drop_duplicates(subset=["id_empresa"], keep="last").rename(
            columns={
                "id_membresia": "id_membresia_actual",
                "fecha_afiliacion": "fecha_afiliacion_actual",
            }
        )
        if not mem_full.empty
        else pd.DataFrame(columns=["id_empresa"])
    )

    agg_asi, agg_enc = _resumir_asistencias_y_encuestas_por_empresa(
        df_asist_bi, df_enc_bi, set(cfg.trimestre_operativo_meses)
    )
    cols_u = [
        c
        for c in (
            "id_empresa",
            "id_membresia_actual",
            "estado_membresia_detalle",
            "es_membresia_activa",
            "segmento_membresia",
            "nivel_membresia",
            "fecha_miembro_desde",
            "fecha_afiliacion_actual",
            "fecha_inicio_vigencia",
            "fecha_fin_vigencia",
        )
        if c in ult_mem.columns
    ]
    base = (
        df_emp.merge(
            silver["dim_kams"].rename(
                columns={
                    "responsable_nombre": "responsable_kam",
                    "tiene_seguimiento_eventos": "kam_con_seguimiento",
                }
            ),
            on="kam_id",
            how="left",
        )
        .merge(ult_mem[cols_u], on="id_empresa", how="left")
        .merge(ciclos_cnt, on="id_empresa", how="left")
        .merge(agg_asi, on="id_empresa", how="left")
        .merge(agg_enc, on="id_empresa", how="left")
    )

    tiene_mem = base["id_membresia_actual"].notna()
    base["es_membresia_activa"] = base["es_membresia_activa"].eq(True)
    base["estado_membresia_detalle"] = base["estado_membresia_detalle"].fillna(
        "Sin membresía en CRM"
    )
    base["tipo_relacion_actho"] = np.where(
        base["es_membresia_activa"],
        "AFILIADO_ACTIVO",
        np.where(tiene_mem, "EX_AFILIADO", "PROSPECTO_NO_AFILIADO"),
    )

    geo_res = [
        (
            mapa_geo[int(cid)]
            if pd.notna(cid) and int(cid) in mapa_geo
            else (None, None, None)
        )
        for cid in base["id_ciudad_empresa"]
    ]
    base["nombre_ciudad"] = [g[0] for g in geo_res]
    base["nombre_departamento"] = [g[1] for g in geo_res]
    base["nombre_pais"] = [g[2] for g in geo_res]

    for col_int in (
        "total_ciclos_membresia",
        "total_eventos_anio",
        "total_asistencias_anio",
        "personas_distintas_anio",
        "asistencias_ultimo_trimestre",
        "total_encuestas_respondidas",
    ):
        base[col_int] = base[col_int].fillna(0).astype(int)

    base = _aplicar_alertas_y_semaforo_hibrido(base, cfg)
    df_out = base[COLS_EMPRESA_360].reset_index(drop=True)
    guardar_tabla_medallion(df_out, cfg.gold_dir, "dim_empresa_360")
    bitacora.registrar_carga(
        "silver -> gold/dim_empresa_360",
        t0,
        leidos=len(df_emp),
        proc=len(df_out),
        ins=len(df_out),
        act=0,
    )
    return df_out


def _contar_cargos_categorizados(serie_cargos: pd.Series) -> dict[str, int]:
    """Agrupa niveles de cargo en las 5 categorías ejecutivas estándar."""
    conteos = {
        "cargos_alta_direccion": 0,
        "cargos_direccion_gerencia": 0,
        "cargos_jefatura_coordinacion": 0,
        "cargos_profesional_analista": 0,
        "cargos_otro_sin_dato": 0,
    }
    for val in serie_cargos:
        txt = (str(val) if pd.notna(val) else "").lower()
        if "alta direcci" in txt or "c-level" in txt or "vp" in txt:
            conteos["cargos_alta_direccion"] += 1
        elif "direcci" in txt or "gerencia" in txt:
            conteos["cargos_direccion_gerencia"] += 1
        elif "jefatura" in txt or "coordinaci" in txt:
            conteos["cargos_jefatura_coordinacion"] += 1
        elif "profesional" in txt or "analista" in txt or "consultor" in txt:
            conteos["cargos_profesional_analista"] += 1
        else:
            conteos["cargos_otro_sin_dato"] += 1
    return conteos


def _calcular_fila_kpi_evento(
    ev: pd.Series,
    df_asist_bi: pd.DataFrame,
    df_enc_bi: pd.DataFrame,
    emp_activas_set: set[str],
    mapa_geo: dict[int, tuple[str, str, str]],
) -> dict[str, Any]:
    """Calcula las métricas completas de convocatoria y satisfacción para un evento."""
    ev_id = int(ev["id_evento"])
    sub = df_asist_bi[df_asist_bi["id_evento"] == ev_id]
    sub_enc = df_enc_bi[
        df_enc_bi["id_evento"].notna() & (df_enc_bi["id_evento"] == ev_id)
    ]

    tot_reg = int(len(sub))
    af_cnt = int((sub["tipo_asistencia"] == "Afiliado").sum())
    emp_ev = set(sub["id_empresa"].dropna())
    tasa_pen = (
        round(
            (len(emp_ev.intersection(emp_activas_set)) / len(emp_activas_set)) * 100.0,
            2,
        )
        if emp_activas_set
        else 0.0
    )

    sat_ev = (
        round(float(sub_enc["promedio_respuesta_1_5"].mean()), 2)
        if not sub_enc.empty and sub_enc["promedio_respuesta_1_5"].notna().any()
        else None
    )
    nps_ev: float | None = None
    if not sub_enc.empty and sub_enc["categoria_nps_0_10"].notna().any():
        val_nps = sub_enc["categoria_nps_0_10"].dropna()
        nps_ev = round(
            (
                (int((val_nps == "PROMOTOR").sum()) - int((val_nps == "DETRACTOR").sum()))
                / len(val_nps)
            )
            * 100.0,
            2,
        )

    cid_ev = ev.get("id_ciudad_evento")
    return {
        "id_evento": ev_id,
        "nombre_evento": ev["nombre_evento"],
        "fecha_inicio_evento": ev["fecha_inicio_evento"],
        "fecha_fin_evento": ev["fecha_fin_evento"],
        "periodo_mes_iso": ev["periodo_mes_iso"],
        "trimestre_iso": ev["trimestre_iso"],
        "linea_oferta_2027": ev["linea_oferta_2027"],
        "experiencia_detalle": ev["experiencia_detalle"],
        "modalidad": ev["modalidad"],
        "nombre_ciudad_evento": (
            mapa_geo[int(cid_ev)][0]
            if pd.notna(cid_ev) and int(cid_ev) in mapa_geo
            else None
        ),
        "total_registros_asistencia": tot_reg,
        "total_cupos_inscritos_prov": (
            int(sub["cantidad_inscritos_prov"].fillna(1).sum()) if tot_reg > 0 else 0
        ),
        "personas_unicas_evento": int(sub["id_persona"].dropna().nunique()),
        "empresas_unicas_evento": len(emp_ev),
        "asistentes_afiliados": af_cnt,
        "asistentes_no_afiliados": tot_reg - af_cnt,
        "tasa_penetracion_afiliados_pct": tasa_pen,
        **_contar_cargos_categorizados(sub["nivel_cargo_evento"]),
        "satisfaccion_promedio_evento_1_5": sat_ev,
        "nps_evento_0_10": nps_ev,
    }


def construir_dim_evento_kpis(
    silver: dict[str, pd.DataFrame],
    df_emp_360: pd.DataFrame,
    df_asist_bi: pd.DataFrame,
    df_enc_bi: pd.DataFrame,
    mapa_geo: dict[int, tuple[str, str, str]],
    *,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye gold_dim_evento_kpis corrigiendo el cruce entero de id_evento."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dim_ev = silver["dim_eventos"].copy()
    dim_ev["id_evento"] = dim_ev["id_evento"].astype(int)
    periodo, trimestre = _derivar_periodo_y_trimestre(dim_ev["fecha_inicio_evento"])
    dim_ev["periodo_mes_iso"] = periodo
    dim_ev["trimestre_iso"] = trimestre

    emp_activas_set = set(
        df_emp_360[df_emp_360["tipo_relacion_actho"] == "AFILIADO_ACTIVO"]["id_empresa"]
    )
    filas = [
        _calcular_fila_kpi_evento(ev, df_asist_bi, df_enc_bi, emp_activas_set, mapa_geo)
        for _, ev in dim_ev.iterrows()
    ]
    df_out = pd.DataFrame(filas)
    guardar_tabla_medallion(df_out, cfg.gold_dir, "dim_evento_kpis")
    bitacora.registrar_carga(
        "silver -> gold/dim_evento_kpis",
        t0,
        leidos=len(dim_ev),
        proc=len(df_out),
        ins=len(df_out),
        act=0,
    )
    return df_out


def _incrementar_celda_evolucion(
    acumulado: dict[tuple[str, str, str, str], dict[str, int]],
    llave: tuple[str, str, str, str],
    metrica: str,
) -> None:
    """Incrementa en 1 el contador mensual aditivo para una llave dimensional."""
    if llave not in acumulado:
        acumulado[llave] = {
            "altas_nuevas_mes": 0,
            "vencimientos_programados_mes": 0,
            "renovaciones_efectivas_mes": 0,
            "retiros_cancelaciones_mes": 0,
        }
    acumulado[llave][metrica] += 1


def construir_fact_evolucion_membresias_mes(
    silver: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye gold_fact_evolucion_membresias_mes con conteos aditivos mensuales."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_mem = silver["membresias"].merge(
        silver["dim_catalogo_membresia"], on="id_cat_membresia", how="left"
    )
    df_mov = silver["fact_movimientos_crm"].merge(
        silver["dim_catalogo_membresia"],
        left_on="id_cat_membresia_movimiento",
        right_on="id_cat_membresia",
        how="left",
    )

    acumulado: dict[tuple[str, str, str, str], dict[str, int]] = {}
    per_max = f"{cfg.anio_analisis + 1}-12"
    estados_retiro = {"Cancelado", "Expirado", "Inactivo"}

    for _, r_m in df_mem.iterrows():
        kam = str(r_m.get("kam_id") or cfg.kam_sin_asignar_id)
        seg = str(r_m.get("segmento_membresia") or "Sin clasificar")
        niv = str(r_m.get("nivel_membresia") or "Sin clasificar")

        f_af = str(r_m.get("fecha_afiliacion") or "")[:7]
        if "2024-01" <= f_af <= per_max:
            _incrementar_celda_evolucion(
                acumulado, (f_af, kam, seg, niv), "altas_nuevas_mes"
            )

        f_fin = str(r_m.get("fecha_fin_vigencia") or "")[:7]
        if "2024-01" <= f_fin <= per_max:
            _incrementar_celda_evolucion(
                acumulado, (f_fin, kam, seg, niv), "vencimientos_programados_mes"
            )
            if str(r_m.get("estado_membresia_detalle")) in estados_retiro:
                _incrementar_celda_evolucion(
                    acumulado, (f_fin, kam, seg, niv), "retiros_cancelaciones_mes"
                )

    for _, r_mv in df_mov.iterrows():
        f_cie = str(r_mv.get("fecha_cierre_o_factura") or "")[:7]
        if "Renovaci" in str(r_mv.get("tipo_movimiento") or "") and len(f_cie) == 7:
            llave_mv = (
                f_cie,
                str(r_mv.get("kam_id") or cfg.kam_sin_asignar_id),
                str(r_mv.get("segmento_membresia") or "Sin clasificar"),
                str(r_mv.get("nivel_membresia") or "Sin clasificar"),
            )
            _incrementar_celda_evolucion(
                acumulado, llave_mv, "renovaciones_efectivas_mes"
            )

    filas = [
        {
            "id_evolucion_mes": f"{per}::{kam}::{seg}::{niv}",
            "periodo_mes_iso": per,
            "kam_id": kam,
            "segmento_membresia": seg,
            "nivel_membresia": niv,
            **cnts,
        }
        for (per, kam, seg, niv), cnts in sorted(acumulado.items())
    ]
    df_out = pd.DataFrame(
        filas,
        columns=[
            "id_evolucion_mes",
            "periodo_mes_iso",
            "kam_id",
            "segmento_membresia",
            "nivel_membresia",
            "altas_nuevas_mes",
            "vencimientos_programados_mes",
            "renovaciones_efectivas_mes",
            "retiros_cancelaciones_mes",
        ],
    )
    guardar_tabla_medallion(df_out, cfg.gold_dir, "fact_evolucion_membresias_mes")
    bitacora.registrar_carga(
        "silver -> gold/fact_evolucion_membresias_mes",
        t0,
        leidos=len(df_mem) + len(df_mov),
        proc=len(df_out),
        ins=len(df_out),
        act=0,
    )
    return df_out


def construir_capa_gold(
    silver: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> dict[str, pd.DataFrame]:
    """Construye las 6 tablas del Esquema Estrella Gold exclusivamente desde Silver."""
    limpiar_archivos_legado_gold(cfg)
    mapa_geo = _construir_mapa_geografico_completo(silver)

    df_asist_bi = construir_fact_asistencias_bi(silver, mapa_geo, cfg, bitacora)
    df_enc_bi = construir_fact_encuestas_bi(
        silver["fact_encuestas_satisfaccion"], mapa_geo, cfg, bitacora
    )
    df_emp_360 = construir_dim_empresa_360(
        silver, df_asist_bi, df_enc_bi, mapa_geo, cfg=cfg, bitacora=bitacora
    )
    df_ev_kpis = construir_dim_evento_kpis(
        silver,
        df_emp_360,
        df_asist_bi,
        df_enc_bi,
        mapa_geo,
        cfg=cfg,
        bitacora=bitacora,
    )
    df_evo_mes = construir_fact_evolucion_membresias_mes(silver, cfg, bitacora)
    df_seg = construir_mart_segmentos_comunicaciones(
        silver, df_emp_360, df_asist_bi, df_enc_bi, cfg=cfg, bitacora=bitacora
    )

    return {
        "dim_empresa_360": df_emp_360,
        "dim_evento_kpis": df_ev_kpis,
        "fact_asistencias_bi": df_asist_bi,
        "fact_encuestas_bi": df_enc_bi,
        "fact_evolucion_membresias_mes": df_evo_mes,
        "mart_segmentos_comunicaciones": df_seg,
    }
