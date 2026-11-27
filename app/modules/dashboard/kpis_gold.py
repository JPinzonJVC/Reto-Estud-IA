"""Cálculos analíticos sobre el Esquema Estrella Gold para los nuevos KPIs ACTHO."""

from typing import Any

import pandas as pd

from app.modules.dashboard.data_store import SnapshotDWH

DIMENSIONES_SEGMENTO_PERMITIDAS: dict[str, str] = {
    "sector": "sector_economico",
    "sector_economico": "sector_economico",
    "subsector": "subsector_economico",
    "subsector_economico": "subsector_economico",
    "tamano": "tamano_empresa",
    "tamano_empresa": "tamano_empresa",
    "rango_empleados": "rango_empleados",
    "empleados": "rango_empleados",
    "nivel": "nivel_membresia",
    "nivel_membresia": "nivel_membresia",
    "segmento_membresia": "segmento_membresia",
}


def calcular_evolucion_membresias(
    snap: SnapshotDWH,
    *,
    kam_id: str | None = None,
    anio: int | None = None,
    ultimos_meses: int = 18,
) -> dict[str, Any]:
    """Consolida la serie mensual de altas, renovaciones y retiros de membresías.

    Args:
        snap: Snapshot del Data Warehouse cargado.
        kam_id: Filtro opcional por ejecutiva KAM.
        anio: Filtro opcional por año calendario.
        ultimos_meses: Cantidad máxima de periodos recientes a retornar.

    Returns:
        Resumen global del flujo y serie mensual ordenada cronológicamente.

    """
    df = snap.fact_evolucion_mes.copy()
    if df.empty:
        return {"resumen": {}, "serie_mensual": []}

    if kam_id:
        df = df[df["kam_id"] == kam_id]
    if anio is not None:
        df = df[df["periodo_mes_iso"].astype(str).str.startswith(f"{anio}-")]
    if df.empty:
        return {"resumen": {}, "serie_mensual": []}

    grp = (
        df.groupby("periodo_mes_iso", as_index=False)
        .agg(
            altas_nuevas=("altas_nuevas_mes", "sum"),
            vencimientos_programados=("vencimientos_programados_mes", "sum"),
            renovaciones_efectivas=("renovaciones_efectivas_mes", "sum"),
            retiros_cancelaciones=("retiros_cancelaciones_mes", "sum"),
        )
        .sort_values("periodo_mes_iso")
    )
    if 0 < ultimos_meses < len(grp):
        grp = grp.tail(ultimos_meses).reset_index(drop=True)

    serie: list[dict[str, Any]] = []
    for _, r in grp.iterrows():
        altas = int(r["altas_nuevas"])
        venc = int(r["vencimientos_programados"])
        ren = int(r["renovaciones_efectivas"])
        ret = int(r["retiros_cancelaciones"])
        serie.append(
            {
                "periodo_mes": str(r["periodo_mes_iso"]),
                "altas_nuevas": altas,
                "vencimientos_programados": venc,
                "renovaciones_efectivas": ren,
                "retiros_cancelaciones": ret,
                "balance_neto": altas - ret,
                "tasa_renovacion_pct": round(ren / venc * 100.0, 1) if venc > 0 else None,
                "tasa_churn_pct": round(ret / venc * 100.0, 1) if venc > 0 else None,
            }
        )

    tot_altas = sum(x["altas_nuevas"] for x in serie)
    tot_venc = sum(x["vencimientos_programados"] for x in serie)
    tot_ren = sum(x["renovaciones_efectivas"] for x in serie)
    tot_ret = sum(x["retiros_cancelaciones"] for x in serie)
    return {
        "resumen": {
            "periodos_evaluados": len(serie),
            "altas_totales": tot_altas,
            "vencimientos_totales": tot_venc,
            "renovaciones_totales": tot_ren,
            "retiros_totales": tot_ret,
            "tasa_renovacion_global_pct": (
                round(tot_ren / tot_venc * 100.0, 1) if tot_venc > 0 else 0.0
            ),
            "tasa_churn_global_pct": (
                round(tot_ret / tot_venc * 100.0, 1) if tot_venc > 0 else 0.0
            ),
        },
        "serie_mensual": serie,
    }


def _armar_fila_kpi_segmento(etiqueta: str, sub: pd.DataFrame) -> dict[str, Any]:
    """Calcula KPIs de afiliación, uso, riesgo y equidad para un grupo de empresas."""
    act = sub[sub["tipo_relacion_actho"] == "AFILIADO_ACTIVO"]
    ex = sub[sub["tipo_relacion_actho"] == "EX_AFILIADO"]
    leads = sub[sub["tipo_relacion_actho"] == "PROSPECTO_NO_AFILIADO"]
    n_act = len(act)
    n_crm = n_act + len(ex)
    con_serv = int((pd.to_numeric(act["total_eventos_anio"], errors="coerce") > 0).sum())
    ev_prom = (
        round(float(pd.to_numeric(act["total_eventos_anio"], errors="coerce").mean()), 2)
        if n_act > 0
        else 0.0
    )
    sat_s = pd.to_numeric(sub["satisfaccion_promedio_1_5"], errors="coerce").dropna()
    muj_s = pd.to_numeric(act["porcentaje_mujeres_num"], errors="coerce").dropna()
    sem = act["semaforo_riesgo_renovacion"].value_counts().to_dict()
    return {
        "categoria": etiqueta,
        "total_empresas": int(len(sub)),
        "afiliados_activos": n_act,
        "ex_afiliados": int(len(ex)),
        "prospectos_leads": int(len(leads)),
        "tasa_permanencia_crm_pct": (
            round(n_act / n_crm * 100.0, 1) if n_crm > 0 else 0.0
        ),
        "empresas_activas_en_servicios": con_serv,
        "porcentaje_uso_servicios": (
            round(con_serv / n_act * 100.0, 1) if n_act > 0 else 0.0
        ),
        "eventos_promedio_activos": ev_prom,
        "satisfaccion_promedio_1_5": (
            round(float(sat_s.mean()), 2) if not sat_s.empty else None
        ),
        "porcentaje_mujeres_promedio": (
            round(float(muj_s.mean()), 1) if not muj_s.empty else None
        ),
        "riesgo_rojo": int(sem.get("ROJO", 0)),
        "riesgo_amarillo": int(sem.get("AMARILLO", 0)),
        "riesgo_verde": int(sem.get("VERDE", 0)),
    }


def calcular_kpis_segmentos_empresariales(
    snap: SnapshotDWH,
    *,
    dimension: str = "sector_economico",
    kam_id: str | None = None,
    pais: str | None = None,
    top_n: int = 15,
) -> dict[str, Any]:
    """Calcula KPIs por sector, subsector, tamaño de empresa, empleados o nivel.

    Args:
        snap: Snapshot del Data Warehouse cargado.
        dimension: Nombre o alias de la dimensión empresarial a agrupar.
        kam_id: Filtro opcional por ejecutiva KAM.
        pais: Filtro opcional por país.
        top_n: Máximo de categorías a retornar ordenadas por afiliados activos.

    Returns:
        Diccionario con la dimensión resuelta y lista de KPIs por categoría.

    """
    col = DIMENSIONES_SEGMENTO_PERMITIDAS.get(dimension, "sector_economico")
    df = snap.dim_empresa_360.copy()
    if df.empty or col not in df.columns:
        return {"dimension": col, "items": []}

    if kam_id:
        df = df[df["kam_id"] == kam_id]
    if pais:
        df = df[df["nombre_pais"] == pais]

    df["_cat"] = df[col].fillna("Sin clasificar").replace("", "Sin clasificar")
    items = [
        _armar_fila_kpi_segmento(str(cat), sub)
        for cat, sub in df.groupby("_cat", dropna=False)
    ]
    items.sort(
        key=lambda x: (x["afiliados_activos"], x["total_empresas"]),
        reverse=True,
    )
    return {
        "dimension": col,
        "total_categorias": len(items),
        "items": items[:top_n],
    }


def calcular_kpis_tipo_evento(
    snap: SnapshotDWH,
    *,
    linea_oferta: str | None = None,
    modalidad: str | None = None,
) -> dict[str, Any]:
    """Calcula KPIs consolidados por línea de oferta 2027, modalidad y evento.

    Args:
        snap: Snapshot del Data Warehouse cargado.
        linea_oferta: Filtro opcional por línea 2027.
        modalidad: Filtro opcional por modalidad.

    Returns:
        KPIs por línea 2027, por modalidad y ranking de eventos desde Gold.

    """
    df_ev = snap.dim_evento_kpis.copy()
    if df_ev.empty:
        return {"por_linea_2027": [], "por_modalidad": [], "eventos": []}

    if linea_oferta:
        df_ev = df_ev[df_ev["linea_oferta_2027"] == linea_oferta]
    if modalidad:
        df_ev = df_ev[df_ev["modalidad"] == modalidad]

    def _agrupar_eventos(col_grp: str) -> list[dict[str, Any]]:
        filas: list[dict[str, Any]] = []
        for clave, sub in df_ev.groupby(df_ev[col_grp].fillna("Sin clasificar")):
            tot_asist = int(sub["total_registros_asistencia"].sum())
            af = int(sub["asistentes_afiliados"].sum())
            leads = int(sub["asistentes_no_afiliados"].sum())
            alta = int(sub["cargos_alta_direccion"].sum()) + int(
                sub["cargos_direccion_gerencia"].sum()
            )
            filas.append(
                {
                    "tipo": str(clave),
                    "total_eventos": int(len(sub)),
                    "eventos_con_asistencia": int(
                        (sub["total_registros_asistencia"] > 0).sum()
                    ),
                    "total_asistencias": tot_asist,
                    "cupos_inscritos_prov": int(sub["total_cupos_inscritos_prov"].sum()),
                    "asistencias_afiliados": af,
                    "asistencias_leads": leads,
                    "porcentaje_leads": (
                        round(leads / tot_asist * 100.0, 1) if tot_asist > 0 else 0.0
                    ),
                    "promedio_asistentes_evento": round(
                        tot_asist / max(len(sub), 1), 1
                    ),
                    "penetracion_promedio_activos_pct": round(
                        float(sub["tasa_penetracion_afiliados_pct"].mean()), 2
                    ),
                    "porcentaje_cargos_directivos": (
                        round(alta / tot_asist * 100.0, 1) if tot_asist > 0 else 0.0
                    ),
                }
            )
        return sorted(filas, key=lambda x: x["total_asistencias"], reverse=True)

    ev_orden = df_ev.sort_values("total_registros_asistencia", ascending=False)
    eventos_list = [
        {
            "id_evento": int(r["id_evento"]),
            "nombre_evento": str(r["nombre_evento"]),
            "fecha_inicio_evento": r["fecha_inicio_evento"],
            "linea_oferta_2027": r["linea_oferta_2027"],
            "modalidad": r["modalidad"],
            "experiencia_detalle": r["experiencia_detalle"],
            "nombre_ciudad_sede": (
                None if pd.isna(r["nombre_ciudad_evento"]) else r["nombre_ciudad_evento"]
            ),
            "total_asistencias": int(r["total_registros_asistencia"]),
            "asistencias_afiliados": int(r["asistentes_afiliados"]),
            "asistencias_leads": int(r["asistentes_no_afiliados"]),
            "empresas_unicas_evento": int(r["empresas_unicas_evento"]),
            "penetracion_activos_pct": float(r["tasa_penetracion_afiliados_pct"]),
            "porcentaje_leads_evento": (
                round(
                    int(r["asistentes_no_afiliados"])
                    / max(int(r["total_registros_asistencia"]), 1)
                    * 100.0,
                    1,
                )
            ),
        }
        for _, r in ev_orden.iterrows()
    ]
    return {
        "por_linea_2027": _agrupar_eventos("linea_oferta_2027"),
        "por_modalidad": _agrupar_eventos("modalidad"),
        "eventos": eventos_list,
    }


def consultar_segmentos_comunicaciones(
    snap: SnapshotDWH,
    *,
    segmento_codigo: str | None = None,
    kam_id: str | None = None,
    solo_aptos: bool = False,
    limit: int = 150,
) -> dict[str, Any]:
    """Consulta el catálogo y registros de los 8 segmentos Gold con Habeas Data.

    Args:
        snap: Snapshot del Data Warehouse cargado.
        segmento_codigo: Código opcional de uno de los 8 segmentos.
        kam_id: Filtro opcional por ejecutiva KAM.
        solo_aptos: Si es True, filtra solo registros con autorización Habeas Data.
        limit: Cantidad máxima de registros de detalle a devolver.

    Returns:
        Resumen de los 8 segmentos y muestra filtrada de registros accionables.

    """
    df = snap.mart_segmentos.copy()
    if df.empty:
        return {"resumen_segmentos": [], "total_filtrado": 0, "items": []}

    if kam_id:
        df = df[df["kam_id"] == kam_id]

    resumen: list[dict[str, Any]] = []
    for (orden, cod, nom), sub in df.groupby(
        ["orden_segmento", "segmento_codigo", "segmento_nombre"]
    ):
        aptos = int(sub["apto_envio_comunicaciones"].eq(True).sum())
        resumen.append(
            {
                "orden": int(orden),
                "segmento_codigo": str(cod),
                "segmento_nombre": str(nom),
                "total_registros": int(len(sub)),
                "aptos_habeas_data": aptos,
                "porcentaje_contactable": (
                    round(aptos / len(sub) * 100.0, 1) if len(sub) > 0 else 0.0
                ),
            }
        )
    resumen.sort(key=lambda x: x["orden"])

    sub_det = df
    if segmento_codigo:
        sub_det = sub_det[sub_det["segmento_codigo"] == segmento_codigo]
    if solo_aptos:
        sub_det = sub_det[sub_det["apto_envio_comunicaciones"].eq(True)]

    total_filtrado = int(len(sub_det))
    items = (
        sub_det.head(limit)
        .where(pd.notna(sub_det.head(limit)), None)
        .to_dict(orient="records")
    )
    return {
        "resumen_segmentos": resumen,
        "total_filtrado": total_filtrado,
        "items": items,
    }
