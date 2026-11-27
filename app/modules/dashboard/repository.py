"""Repositorio analítico del Dashboard conectado al DWH Gold Estrella y Silver 3NF."""

from datetime import date, timedelta
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.modules.dashboard.data_store import (
    SnapshotDWH,
    cargar_snapshot_dwh,
    lista_distintos,
)
from app.modules.dashboard.kpis_gold import (
    calcular_evolucion_membresias,
    calcular_kpis_segmentos_empresariales,
    calcular_kpis_tipo_evento,
    consultar_segmentos_comunicaciones,
)

PILARES_EMPRESA: tuple[tuple[str, str], ...] = (
    ("vinculado_comunidades", "Vinculado a comunidades"),
    ("pilar_hr_estrategico", "HR Estratégico"),
    ("pilar_mas_que_salario", "Más que un Salario"),
    ("pilar_talento_que_elige", "Talento que Elige"),
    ("pilar_gente_que_crece", "Gente que Crece"),
    ("comunidad_mujeres_hr", "Comunidad Mujeres HR"),
    ("es_influenciador", "Influenciador"),
)


def _limpiar_val(val: Any) -> Any:
    """Convierte valores NaN/NA de pandas en None serializable a JSON."""
    return None if pd.isna(val) else val


def _filtrar_empresas_360(df: pd.DataFrame, filtros: dict[str, Any]) -> pd.DataFrame:
    """Aplica filtros comerciales opcionales sobre gold_dim_empresa_360."""
    res = df.copy()
    if res.empty:
        return res
    pares = (
        ("kam_id", "kam_id"),
        ("nivel_membresia", "nivel_membresia"),
        ("sector", "sector_economico"),
        ("subsector", "subsector_economico"),
        ("tamano_empresa", "tamano_empresa"),
        ("rango_empleados", "rango_empleados"),
        ("estado_membresia", "estado_membresia_detalle"),
        ("ciudad", "nombre_ciudad"),
        ("pais", "nombre_pais"),
        ("semaforo", "semaforo_riesgo_renovacion"),
    )
    for clave_f, col_df in pares:
        valor = filtros.get(clave_f)
        if valor and col_df in res.columns:
            res = res[res[col_df] == valor]
    if filtros.get("solo_activos") is True:
        res = res[res["es_membresia_activa"].eq(True)]
    return res


def _filtrar_asistencias_bi(df: pd.DataFrame, filtros: dict[str, Any]) -> pd.DataFrame:
    """Aplica filtros temporales y de oferta sobre gold_fact_asistencias_bi."""
    res = df.copy()
    if res.empty:
        return res
    if filtros.get("fecha_desde"):
        res = res[res["fecha_inicio_evento"].fillna("") >= str(filtros["fecha_desde"])]
    if filtros.get("fecha_hasta"):
        res = res[res["fecha_inicio_evento"].fillna("") <= str(filtros["fecha_hasta"])]
    if filtros.get("kam_id"):
        res = res[res["kam_id_asistencia"] == filtros["kam_id"]]
    if filtros.get("ciudad_evento"):
        res = res[res["nombre_ciudad_asistente"] == filtros["ciudad_evento"]]
    if filtros.get("linea_oferta"):
        res = res[res["linea_oferta_2027"] == filtros["linea_oferta"]]
    if filtros.get("modalidad"):
        res = res[res["modalidad"] == filtros["modalidad"]]
    return res


class DashboardSilverRepository:
    """Repositorio unificado del tablero sobre Gold Estrella y Silver 3NF."""

    def __init__(self, session: Session | None = None) -> None:
        """Inicializa el repositorio con sesión SQLAlchemy o respaldo Parquet."""
        self.session = session
        self._snap: SnapshotDWH | None = None

    @property
    def snap(self) -> SnapshotDWH:
        """Obtiene el snapshot cargado perezosamente para la petición actual."""
        if self._snap is None:
            self._snap = cargar_snapshot_dwh(self.session)
        return self._snap

    def obtener_filtros(self) -> dict[str, list[str]]:
        """Retorna todos los catálogos de filtros del tablero."""
        emp = self.snap.dim_empresa_360
        ev = self.snap.dim_evento_kpis
        asi = self.snap.fact_asistencias_bi
        return {
            "kams": lista_distintos(emp, "kam_id"),
            "niveles_membresia": lista_distintos(emp, "nivel_membresia"),
            "sectores": lista_distintos(emp, "sector_economico"),
            "subsectores": lista_distintos(emp, "subsector_economico"),
            "tamanos_empresa": lista_distintos(emp, "tamano_empresa"),
            "rangos_empleados": lista_distintos(emp, "rango_empleados"),
            "estados_membresia": lista_distintos(emp, "estado_membresia_detalle"),
            "ciudades": lista_distintos(emp, "nombre_ciudad"),
            "departamentos": lista_distintos(emp, "nombre_departamento"),
            "paises": lista_distintos(emp, "nombre_pais"),
            "semaforos_riesgo": ["ROJO", "AMARILLO", "VERDE"],
            "lineas_oferta": lista_distintos(ev, "linea_oferta_2027"),
            "modalidades_evento": lista_distintos(ev, "modalidad"),
            "periodos_asistencia": lista_distintos(asi, "periodo_mes_iso"),
            "ciudades_evento": lista_distintos(asi, "nombre_ciudad_asistente"),
        }

    def obtener_resumen(self, fecha_referencia: date) -> dict[str, Any]:
        """Calcula los KPIs ejecutivos de afiliación, semáforo, eventos y NPS."""
        emp = self.snap.dim_empresa_360
        asi = self.snap.fact_asistencias_bi
        enc = self.snap.fact_encuestas_bi
        ref = fecha_referencia.isoformat()

        act = emp[emp["es_membresia_activa"].eq(True)] if not emp.empty else emp
        n_act = int(len(act))
        n_ex = (
            int((emp["tipo_relacion_actho"] == "EX_AFILIADO").sum())
            if not emp.empty
            else 0
        )
        n_leads = (
            int((emp["tipo_relacion_actho"] == "PROSPECTO_NO_AFILIADO").sum())
            if not emp.empty
            else 0
        )

        venc: dict[str, int] = {}
        for days in (30, 60, 90):
            lim = (fecha_referencia + timedelta(days=days)).isoformat()
            venc[str(days)] = (
                int(
                    (
                        (act["fecha_fin_vigencia"].fillna("") >= ref)
                        & (act["fecha_fin_vigencia"].fillna("") <= lim)
                    ).sum()
                )
                if not act.empty
                else 0
            )

        con_serv = (
            int((pd.to_numeric(act["total_eventos_anio"], errors="coerce") > 0).sum())
            if not act.empty
            else 0
        )
        emp_unicas = int(asi["id_empresa"].dropna().nunique()) if not asi.empty else 0
        af_asist = (
            int((asi["tipo_asistencia"] == "Afiliado").sum()) if not asi.empty else 0
        )
        sat_s = (
            pd.to_numeric(enc["promedio_respuesta_1_5"], errors="coerce").dropna()
            if not enc.empty
            else pd.Series(dtype=float)
        )
        nps_s = (
            pd.to_numeric(
                enc["pregunta_recomendacion_nps_0_10"], errors="coerce"
            ).dropna()
            if not enc.empty
            else pd.Series(dtype=float)
        )
        nps_score = (
            round(
                float(((nps_s >= 9).sum() - (nps_s <= 6).sum()) / len(nps_s) * 100.0),
                1,
            )
            if not nps_s.empty
            else None
        )
        sem_counts = (
            act["semaforo_riesgo_renovacion"].value_counts().to_dict()
            if not act.empty
            else {}
        )

        return {
            "fecha_referencia": ref,
            "total_empresas": int(len(emp)),
            "afiliados_activos": n_act,
            "ex_afiliados": n_ex,
            "prospectos_leads": n_leads,
            "tasa_retencion_historica_pct": (
                round(n_act / (n_act + n_ex) * 100.0, 1) if (n_act + n_ex) else 0.0
            ),
            "vencimientos_proximos": venc,
            "semaforo_riesgo": {
                "ROJO": int(sem_counts.get("ROJO", 0)),
                "AMARILLO": int(sem_counts.get("AMARILLO", 0)),
                "VERDE": int(sem_counts.get("VERDE", 0)),
            },
            "empresas_con_servicio": con_serv,
            "empresas_unicas_asistentes": emp_unicas,
            "porcentaje_afiliados_en_servicios": (
                round(con_serv / n_act * 100.0, 2) if n_act else 0.0
            ),
            "total_asistencias": int(len(asi)),
            "asistentes_afiliados": af_asist,
            "asistentes_no_afiliados": int(len(asi)) - af_asist,
            "total_respuestas_satisfaccion": int(len(enc)),
            "promedio_satisfaccion_1_5": (
                round(float(sat_s.mean()), 2) if not sat_s.empty else 0.0
            ),
            "nps_oficial_disponible": bool(not nps_s.empty),
            "nps_oficial_score": nps_score,
            "capa_datos": "dwh_gold_silver",
            "fuente_datos": self.snap.fuente,
        }

    def listar_afiliados(self, **kwargs: Any) -> dict[str, Any]:
        """Lista cartera de empresas desde gold_dim_empresa_360 con paginación."""
        offset = int(kwargs.get("offset", 0))
        limit = int(kwargs.get("limit", 50))
        df = _filtrar_empresas_360(self.snap.dim_empresa_360, kwargs)
        if df.empty:
            return {"total": 0, "offset": offset, "limit": limit, "items": []}

        df = df.sort_values(
            ["fecha_fin_vigencia", "id_empresa"], na_position="last"
        ).reset_index(drop=True)
        total = int(len(df))
        fin = offset + limit
        sub = df.iloc[offset:fin]
        items = [
            {
                "id_empresa": str(r["id_empresa"]),
                "kam_id": _limpiar_val(r.get("kam_id")),
                "kam_nombre": _limpiar_val(r.get("responsable_kam")),
                "membresia_activa": bool(r.get("es_membresia_activa") is True),
                "nivel_membresia": _limpiar_val(r.get("nivel_membresia")),
                "sector_economico": _limpiar_val(r.get("sector_economico")),
                "subsector_economico": _limpiar_val(r.get("subsector_economico")),
                "tamano_empresa": _limpiar_val(r.get("tamano_empresa")),
                "rango_empleados": _limpiar_val(r.get("rango_empleados")),
                "estado_membresia": _limpiar_val(r.get("estado_membresia_detalle")),
                "ciudad": _limpiar_val(r.get("nombre_ciudad")),
                "pais": _limpiar_val(r.get("nombre_pais")),
                "fecha_afiliacion": _limpiar_val(r.get("fecha_afiliacion_actual")),
                "fecha_miembro_desde": _limpiar_val(r.get("fecha_miembro_desde")),
                "fecha_expiracion": _limpiar_val(r.get("fecha_fin_vigencia")),
                "semaforo_riesgo": _limpiar_val(r.get("semaforo_riesgo_renovacion")),
                "puntaje_riesgo": _limpiar_val(r.get("puntaje_riesgo_heuristico")),
                "eventos_anio": int(r.get("total_eventos_anio") or 0),
                "personas_anio": int(r.get("personas_distintas_anio") or 0),
            }
            for _, r in sub.iterrows()
        ]
        return {"total": total, "offset": offset, "limit": limit, "items": items}

    def obtener_participacion(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Agrupa participación por evento, línea 2027 y modalidad."""
        asi = _filtrar_asistencias_bi(self.snap.fact_asistencias_bi, kwargs)
        ev_kpis = self.snap.dim_evento_kpis
        if asi.empty or ev_kpis.empty:
            return []

        ev_map = {int(r["id_evento"]): r.to_dict() for _, r in ev_kpis.iterrows()}
        filas: list[dict[str, Any]] = []
        for id_ev, sub in asi.groupby("id_evento"):
            ev_int = int(str(id_ev))
            info = ev_map.get(ev_int, {})
            af = int((sub["tipo_asistencia"] == "Afiliado").sum())
            no_af = int(len(sub)) - af
            filas.append(
                {
                    "id_evento": ev_int,
                    "nombre_evento": _limpiar_val(info.get("nombre_evento")),
                    "linea_oferta": _limpiar_val(info.get("linea_oferta_2027")),
                    "modalidad": _limpiar_val(info.get("modalidad")),
                    "fecha_evento": _limpiar_val(info.get("fecha_inicio_evento")),
                    "ciudad_sede": _limpiar_val(info.get("nombre_ciudad_evento")),
                    "asistencias": int(len(sub)),
                    "asistentes_afiliados": af,
                    "asistentes_no_afiliados": no_af,
                    "empresas_distintas": int(sub["id_empresa"].dropna().nunique()),
                    "personas_distintas": int(sub["id_persona"].dropna().nunique()),
                    "penetracion_activos_pct": float(
                        info.get("tasa_penetracion_afiliados_pct") or 0.0
                    ),
                }
            )
        filas.sort(key=lambda x: str(x["fecha_evento"] or ""), reverse=True)
        return filas

    def obtener_audiencia(self, **kwargs: Any) -> dict[str, Any]:
        """Desglosa asistencias por cargo al evento, línea 2027 y modalidad."""
        asi = _filtrar_asistencias_bi(self.snap.fact_asistencias_bi, kwargs)
        if asi.empty:
            return {"niveles_cargo": [], "lineas_oferta": [], "modalidades": []}

        cargos = (
            asi.assign(_c=asi["nivel_cargo_evento"].fillna("Sin dato"))
            .groupby("_c", as_index=False)
            .size()
            .sort_values("size", ascending=False)
        )

        def _grp_af(col: str, out_key: str, etiqueta_na: str) -> list[dict[str, Any]]:
            res: list[dict[str, Any]] = []
            for k, sub in asi.groupby(asi[col].fillna(etiqueta_na)):
                af = int((sub["tipo_asistencia"] == "Afiliado").sum())
                res.append(
                    {
                        out_key: str(k),
                        "asistencias": int(len(sub)),
                        "afiliados": af,
                        "no_afiliados": int(len(sub)) - af,
                    }
                )
            return sorted(res, key=lambda x: x["asistencias"], reverse=True)

        return {
            "niveles_cargo": [
                {"nivel_cargo": str(r["_c"]), "asistencias": int(r["size"])}
                for _, r in cargos.iterrows()
            ],
            "lineas_oferta": _grp_af("linea_oferta_2027", "linea_oferta", "Sin línea"),
            "modalidades": _grp_af("modalidad", "modalidad", "Sin modalidad"),
        }

    def obtener_satisfaccion(
        self, *, fecha_desde: str | None = None, fecha_hasta: str | None = None
    ) -> list[dict[str, Any]]:
        """Calcula satisfacción Likert 1-5 y estado de NPS oficial 0-10 por mes."""
        enc = self.snap.fact_encuestas_bi.copy()
        if enc.empty:
            return []
        if fecha_desde:
            enc = enc[enc["fecha_encuesta"].fillna("") >= fecha_desde]
        if fecha_hasta:
            enc = enc[enc["fecha_encuesta"].fillna("") <= fecha_hasta]
        if enc.empty:
            return []

        ev_map = {
            int(r["id_evento"]): str(r["nombre_evento"])
            for _, r in self.snap.silver_eventos.iterrows()
        }
        salida: list[dict[str, Any]] = []
        for (id_ev, per, t_enc), sub in enc.groupby(
            [
                pd.to_numeric(enc["id_evento"], errors="coerce").fillna(-1).astype(int),
                enc["periodo_mes_iso"].fillna("SIN_FECHA"),
                enc["tipo_encuesta"].fillna("POST_EVENTO"),
            ]
        ):
            n_resp = int(len(sub))
            alta = int((sub["nivel_satisfaccion_1_5"] == "ALTA").sum())
            baja = int((sub["nivel_satisfaccion_1_5"] == "BAJA").sum())
            prom_s = pd.to_numeric(sub["promedio_respuesta_1_5"], errors="coerce")
            nps_s = pd.to_numeric(
                sub["pregunta_recomendacion_nps_0_10"], errors="coerce"
            ).dropna()
            nps_oficial = (
                round(
                    float(((nps_s >= 9).sum() - (nps_s <= 6).sum()) / len(nps_s) * 100),
                    1,
                )
                if not nps_s.empty
                else None
            )
            ev_num = int(str(id_ev))
            ev_id_clean = ev_num if ev_num != -1 else None
            salida.append(
                {
                    "id_evento": ev_id_clean,
                    "nombre_evento": ev_map.get(ev_id_clean) if ev_id_clean else None,
                    "periodo_mes": str(per),
                    "tipo_encuesta": str(t_enc),
                    "respuestas": n_resp,
                    "promedio_satisfaccion": round(float(prom_s.mean() or 0.0), 2),
                    "promotores": alta,
                    "detractores": baja,
                    "satisfaccion_alta_pct": round(alta / n_resp * 100.0, 1),
                    "nps_adaptado_1_5": round((alta - baja) / n_resp * 100.0, 1),
                    "nps_oficial_0_10": nps_oficial,
                }
            )
        salida.sort(key=lambda x: x["periodo_mes"], reverse=True)
        return salida

    def obtener_dimensiones_satisfaccion(
        self, *, fecha_desde: str | None = None, fecha_hasta: str | None = None
    ) -> dict[str, Any]:
        """Calcula las 4 dimensiones Likert, ranking NLP de temas y escala NPS."""
        enc = self.snap.fact_encuestas_bi.copy()
        if fecha_desde and not enc.empty:
            enc = enc[enc["fecha_encuesta"].fillna("") >= fecha_desde]
        if fecha_hasta and not enc.empty:
            enc = enc[enc["fecha_encuesta"].fillna("") <= fecha_hasta]
        if enc.empty:
            return {
                "por_modalidad": [],
                "total_con_temarios": 0,
                "temarios_recientes": [],
                "temas_nlp": [],
                "resumen_escalas": {},
            }

        por_mod: list[dict[str, Any]] = []
        for mod, sub in enc.groupby(enc["modalidad_encuesta"].fillna("Sin modalidad")):
            por_mod.append(
                {
                    "modalidad": str(mod),
                    "respuestas": int(len(sub)),
                    "locacion_plataforma": round(
                        float(
                            pd.to_numeric(
                                sub["calif_locacion_o_plataforma"], errors="coerce"
                            ).mean()
                            or 0.0
                        ),
                        2,
                    ),
                    "convocatoria_publicidad": round(
                        float(
                            pd.to_numeric(
                                sub["calif_convocatoria_publicidad"], errors="coerce"
                            ).mean()
                            or 0.0
                        ),
                        2,
                    ),
                    "conferencistas": round(
                        float(
                            pd.to_numeric(
                                sub["calif_conferencistas"], errors="coerce"
                            ).mean()
                            or 0.0
                        ),
                        2,
                    ),
                    "relevancia_temas": round(
                        float(
                            pd.to_numeric(
                                sub["calif_relevancia_temas"], errors="coerce"
                            ).mean()
                            or 0.0
                        ),
                        2,
                    ),
                    "promedio_general": round(
                        float(
                            pd.to_numeric(
                                sub["promedio_respuesta_1_5"], errors="coerce"
                            ).mean()
                            or 0.0
                        ),
                        2,
                    ),
                }
            )

        con_tem = enc[
            enc["temarios_sugeridos"].notna()
            & (enc["temarios_sugeridos"].astype(str).str.strip() != "")
        ].sort_values("fecha_encuesta", ascending=False)

        temas_nlp: list[dict[str, Any]] = []
        sub_nlp = enc[enc["categoria_tema_nlp"].notna()]
        for cat, grp_t in sub_nlp.groupby("categoria_tema_nlp"):
            temas_nlp.append(
                {
                    "categoria": str(cat),
                    "menciones": int(len(grp_t)),
                    "porcentaje": round(len(grp_t) / max(len(sub_nlp), 1) * 100.0, 1),
                    "satisfaccion_promedio": round(
                        float(
                            pd.to_numeric(
                                grp_t["promedio_respuesta_1_5"], errors="coerce"
                            ).mean()
                            or 0.0
                        ),
                        2,
                    ),
                }
            )
        temas_nlp.sort(key=lambda x: x["menciones"], reverse=True)

        niv_counts = enc["nivel_satisfaccion_1_5"].value_counts().to_dict()
        nps_validos = int(enc["pregunta_recomendacion_nps_0_10"].notna().sum())
        return {
            "por_modalidad": sorted(por_mod, key=lambda x: x["modalidad"]),
            "total_con_temarios": int(len(con_tem)),
            "temarios_recientes": [
                {
                    "fecha": _limpiar_val(r["fecha_encuesta"]),
                    "modalidad": _limpiar_val(r["modalidad_encuesta"]),
                    "categoria_nlp": _limpiar_val(r.get("categoria_tema_nlp")),
                    "temario": str(r["temarios_sugeridos"]),
                }
                for _, r in con_tem.head(12).iterrows()
            ],
            "temas_nlp": temas_nlp,
            "resumen_escalas": {
                "likert_alta": int(niv_counts.get("ALTA", 0)),
                "likert_media": int(niv_counts.get("MEDIA", 0)),
                "likert_baja": int(niv_counts.get("BAJA", 0)),
                "respuestas_nps_0_10": nps_validos,
                "estado_nps_0_10": (
                    "ACTIVO" if nps_validos > 0 else "PENDIENTE_CAPTURA_0_10"
                ),
            },
        }

    def obtener_renovaciones(
        self,
        *,
        periodo_desde: str | None = None,
        periodo_hasta: str | None = None,
        kam_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Agrupa movimientos comerciales CRM por periodo derivado y KAM."""
        mov = self.snap.silver_movimientos.copy()
        if mov.empty:
            return []
        fechas = mov["fecha_cierre_o_factura"].fillna(mov["fecha_expiracion_afiliacion"])
        mov["periodo_mes"] = (
            pd.to_datetime(fechas, errors="coerce")
            .dt.strftime("%Y-%m")
            .fillna("SIN_FECHA")
        )
        if periodo_desde:
            mov = mov[mov["periodo_mes"] >= periodo_desde]
        if periodo_hasta:
            mov = mov[mov["periodo_mes"] <= periodo_hasta]
        if kam_id:
            mov = mov[mov["kam_id"] == kam_id]
        if mov.empty:
            return []

        es_ren = mov["tipo_movimiento"].fillna("").str.contains("Renov", case=False)
        mov = mov.assign(_ren=es_ren)
        res: list[dict[str, Any]] = []
        for (per, k_id), sub in mov.groupby(["periodo_mes", "kam_id"]):
            res.append(
                {
                    "periodo_mes": str(per),
                    "kam_id": str(k_id),
                    "movimientos": int(len(sub)),
                    "renovaciones": int(sub["_ren"].sum()),
                    "cierres_facturados": int(sub["es_cierre_facturado"].eq(True).sum()),
                }
            )
        res.sort(key=lambda x: (x["periodo_mes"], x["kam_id"]), reverse=True)
        return res

    def obtener_pilares_y_comunidades(self, **kwargs: Any) -> dict[str, Any]:
        """Calcula adopción de pilares estratégicos y diversidad sobre activos."""
        filtros = {**kwargs, "solo_activos": True}
        act_360 = _filtrar_empresas_360(self.snap.dim_empresa_360, filtros)
        ids_act = set(act_360["id_empresa"]) if not act_360.empty else set()
        sil_emp = self.snap.silver_empresas
        sub = (
            sil_emp[sil_emp["id_empresa"].isin(ids_act)] if not sil_emp.empty else sil_emp
        )
        n_act = int(len(sub))

        pilares = [
            {
                "clave": col_name,
                "nombre": label,
                "empresas": int(sub[col_name].eq(True).sum()) if n_act else 0,
                "porcentaje": (
                    round(int(sub[col_name].eq(True).sum()) / n_act * 100.0, 1)
                    if n_act
                    else 0.0
                ),
            }
            for col_name, label in PILARES_EMPRESA
            if col_name in sub.columns
        ]
        muj = (
            pd.to_numeric(sub["porcentaje_mujeres_num"], errors="coerce").dropna()
            if n_act
            else pd.Series(dtype=float)
        )
        return {
            "total_activos": n_act,
            "pilares": pilares,
            "porcentaje_mujeres_promedio": (
                round(float(muj.mean()), 1) if not muj.empty else None
            ),
            "empresas_con_dato_mujeres": int(len(muj)),
        }

    def obtener_resumen_kams(self, fecha_referencia: date) -> list[dict[str, Any]]:
        """Construye comparativa de cartera, semáforo de riesgo y uso por KAM."""
        kams = self.snap.silver_kams
        if kams.empty:
            return []

        ref = fecha_referencia.isoformat()
        lim90 = (fecha_referencia + timedelta(days=90)).isoformat()
        emp = self.snap.dim_empresa_360
        act = emp[emp["es_membresia_activa"].eq(True)] if not emp.empty else emp
        asist_kam = (
            self.snap.fact_asistencias_bi.groupby("kam_id_asistencia").size().to_dict()
            if not self.snap.fact_asistencias_bi.empty
            else {}
        )

        res: list[dict[str, Any]] = []
        for _, k in kams.iterrows():
            kid = str(k["kam_id"])
            sub_a = act[act["kam_id"] == kid] if not act.empty else pd.DataFrame()
            n_act = int(len(sub_a))
            con_srv = int((sub_a["total_eventos_anio"] > 0).sum()) if n_act > 0 else 0
            venc90 = (
                int(
                    (
                        (sub_a["fecha_fin_vigencia"].fillna("") >= ref)
                        & (sub_a["fecha_fin_vigencia"].fillna("") <= lim90)
                    ).sum()
                )
                if n_act > 0
                else 0
            )
            sem = (
                sub_a["semaforo_riesgo_renovacion"].value_counts().to_dict()
                if n_act > 0
                else {}
            )
            sub_m = (
                self.snap.silver_movimientos[
                    self.snap.silver_movimientos["kam_id"] == kid
                ]
                if not self.snap.silver_movimientos.empty
                else pd.DataFrame()
            )
            ren_cnt = (
                int(
                    sub_m["tipo_movimiento"]
                    .fillna("")
                    .str.contains("Renov", case=False)
                    .sum()
                )
                if not sub_m.empty
                else 0
            )
            cie_cnt = (
                int(sub_m["es_cierre_facturado"].eq(True).sum()) if not sub_m.empty else 0
            )
            res.append(
                {
                    "kam_id": kid,
                    "responsable_nombre": str(k["responsable_nombre"]),
                    "afiliados_activos": n_act,
                    "vencen_90d": venc90,
                    "empresas_con_asistencia": con_srv,
                    "porcentaje_en_servicios": (
                        round(con_srv / n_act * 100.0, 1) if n_act else 0.0
                    ),
                    "asistencias_totales": int(asist_kam.get(kid, 0)),
                    "renovaciones": ren_cnt,
                    "cierres_facturados": cie_cnt,
                    "riesgo_rojo": int(sem.get("ROJO", 0)),
                    "riesgo_amarillo": int(sem.get("AMARILLO", 0)),
                    "riesgo_verde": int(sem.get("VERDE", 0)),
                }
            )
        return sorted(res, key=lambda x: x["afiliados_activos"], reverse=True)

    def obtener_distribucion_afiliados(self, **kwargs: Any) -> dict[str, Any]:
        """Calcula distribución de activos y curva de vencimientos 30/60/90 días."""
        fecha_ref: date = kwargs.get("fecha_referencia") or date.today()
        act = _filtrar_empresas_360(
            self.snap.dim_empresa_360, {**kwargs, "solo_activos": True}
        )
        n_act = int(len(act))

        def _agrupar(col: str, key_name: str, top_n: int = 10) -> list[dict[str, Any]]:
            if act.empty or col not in act.columns:
                return []
            vc = act[col].fillna("Sin dato").replace("", "Sin dato").value_counts()
            return [
                {
                    key_name: str(etq),
                    "empresas": int(cnt),
                    "porcentaje": round(int(cnt) / n_act * 100.0, 1) if n_act else 0.0,
                }
                for etq, cnt in vc.head(top_n).items()
            ]

        ref = fecha_ref.isoformat()
        d30 = (fecha_ref + timedelta(days=30)).isoformat()
        d60 = (fecha_ref + timedelta(days=60)).isoformat()
        d90 = (fecha_ref + timedelta(days=90)).isoformat()
        global_v = {"vencidos": 0, "d0_30": 0, "d31_60": 0, "d61_90": 0, "total_90d": 0}
        por_kam: dict[str, dict[str, Any]] = {}

        for _, r in act.iterrows():
            f_exp = _limpiar_val(r.get("fecha_fin_vigencia"))
            if not f_exp:
                continue
            f_str = str(f_exp)
            kid = str(r.get("kam_id") or "KAM-UNASSIGNED")
            bkt = por_kam.setdefault(
                kid,
                {
                    "kam_id": kid,
                    "responsable_nombre": str(r.get("responsable_kam") or kid),
                    "vencidos": 0,
                    "d0_30": 0,
                    "d31_60": 0,
                    "d61_90": 0,
                    "total_90d": 0,
                },
            )
            if f_str < ref:
                global_v["vencidos"] += 1
                bkt["vencidos"] += 1
            elif f_str <= d30:
                global_v["d0_30"] += 1
                global_v["total_90d"] += 1
                bkt["d0_30"] += 1
                bkt["total_90d"] += 1
            elif f_str <= d60:
                global_v["d31_60"] += 1
                global_v["total_90d"] += 1
                bkt["d31_60"] += 1
                bkt["total_90d"] += 1
            elif f_str <= d90:
                global_v["d61_90"] += 1
                global_v["total_90d"] += 1
                bkt["d61_90"] += 1
                bkt["total_90d"] += 1

        venc_kam = sorted(
            [v for v in por_kam.values() if v["total_90d"] > 0 or v["vencidos"] > 0],
            key=lambda x: (x["total_90d"], x["vencidos"]),
            reverse=True,
        )
        return {
            "fecha_referencia": ref,
            "total_activos": n_act,
            "por_nivel": _agrupar("nivel_membresia", "nivel", 10),
            "por_sector": _agrupar("sector_economico", "sector", 10),
            "por_subsector": _agrupar("subsector_economico", "subsector", 10),
            "por_tamano": _agrupar("tamano_empresa", "tamano", 8),
            "por_rango_empleados": _agrupar("rango_empleados", "rango_empleados", 8),
            "vencimientos_global": global_v,
            "vencimientos_por_kam": venc_kam,
        }

    def obtener_segmentos(self, fecha_referencia: date, limit: int) -> dict[str, Any]:
        """Devuelve alertas rápidas de vencimientos, inactividad y leads."""
        ref = fecha_referencia.isoformat()
        lim90 = (fecha_referencia + timedelta(days=90)).isoformat()
        act = self.snap.dim_empresa_360[
            self.snap.dim_empresa_360["es_membresia_activa"].eq(True)
        ]
        asi = self.snap.fact_asistencias_bi

        venc = act[
            (act["fecha_fin_vigencia"].fillna("") >= ref)
            & (act["fecha_fin_vigencia"].fillna("") <= lim90)
        ].sort_values("fecha_fin_vigencia")
        sin_p = act[act["total_eventos_anio"] == 0].sort_values("id_empresa")
        leads = asi[asi["tipo_asistencia"] != "Afiliado"].head(limit)

        return {
            "fecha_referencia": ref,
            "vencimientos_proximos": [
                {
                    "id_empresa": str(r["id_empresa"]),
                    "kam_id": str(r["kam_id"]),
                    "fecha_expiracion": _limpiar_val(r["fecha_fin_vigencia"]),
                }
                for _, r in venc.head(limit).iterrows()
            ],
            "afiliados_sin_participacion": [
                {"id_empresa": str(r["id_empresa"]), "kam_id": str(r["kam_id"])}
                for _, r in sin_p.head(limit).iterrows()
            ],
            "asistentes_no_afiliados": [
                {
                    "id_asistencia": str(r["id_asistencia"]),
                    "id_persona": _limpiar_val(r["id_persona"]),
                    "id_empresa": _limpiar_val(r["id_empresa"]),
                    "id_evento": int(r["id_evento"]),
                }
                for _, r in leads.iterrows()
            ],
        }

    def obtener_riesgo_participacion_silver(self, **kwargs: Any) -> dict[str, Any]:
        """Clasifica activos en sin participación, monocontacto y multicontacto."""
        limit = int(kwargs.get("limit", 500))
        act = _filtrar_empresas_360(
            self.snap.dim_empresa_360, {**kwargs, "solo_activos": True}
        ).sort_values(["fecha_fin_vigencia", "id_empresa"], na_position="last")

        sin_p: list[dict[str, Any]] = []
        mono: list[dict[str, Any]] = []
        multi_cnt = 0
        suma_per = 0
        emp_part = 0

        for _, r in act.iterrows():
            personas = int(r.get("personas_distintas_anio") or 0)
            asist = int(r.get("total_asistencias_anio") or 0)
            fila = {
                "id_empresa": str(r["id_empresa"]),
                "kam_id": _limpiar_val(r.get("kam_id")),
                "kam_nombre": _limpiar_val(r.get("responsable_kam") or r.get("kam_id")),
                "nivel_membresia": _limpiar_val(r.get("nivel_membresia")),
                "sector_economico": _limpiar_val(r.get("sector_economico")),
                "ciudad": _limpiar_val(r.get("nombre_ciudad")),
                "fecha_expiracion": _limpiar_val(r.get("fecha_fin_vigencia")),
                "semaforo_riesgo": _limpiar_val(r.get("semaforo_riesgo_renovacion")),
                "personas_participantes": personas,
                "asistencias": asist,
            }
            if asist == 0:
                sin_p.append(fila)
            elif personas <= 1:
                mono.append(fila)
                suma_per += personas
                emp_part += 1
            else:
                multi_cnt += 1
                suma_per += personas
                emp_part += 1

        return {
            "resumen": {
                "total_activos": int(len(act)),
                "sin_participacion": len(sin_p),
                "monocontacto": len(mono),
                "multicontacto": multi_cnt,
                "promedio_personas_participantes": (
                    round(suma_per / emp_part, 2) if emp_part else 0.0
                ),
            },
            "lista_sin_participacion": sin_p[:limit],
            "lista_monocontacto": mono[:limit],
        }

    def obtener_evolucion_membresias(
        self,
        *,
        kam_id: str | None = None,
        anio: int | None = None,
        ultimos_meses: int = 18,
    ) -> dict[str, Any]:
        """Retorna la evolución mensual de membresías desde Gold."""
        return calcular_evolucion_membresias(
            self.snap, kam_id=kam_id, anio=anio, ultimos_meses=ultimos_meses
        )

    def obtener_kpis_segmentos_empresariales(
        self,
        *,
        dimension: str = "sector_economico",
        kam_id: str | None = None,
        pais: str | None = None,
        top_n: int = 15,
    ) -> dict[str, Any]:
        """Retorna KPIs por sector, subsector, tamaño, rango empleados o nivel."""
        return calcular_kpis_segmentos_empresariales(
            self.snap, dimension=dimension, kam_id=kam_id, pais=pais, top_n=top_n
        )

    def obtener_kpis_tipo_evento(
        self,
        *,
        linea_oferta: str | None = None,
        modalidad: str | None = None,
    ) -> dict[str, Any]:
        """Retorna KPIs consolidados por línea 2027, modalidad y evento."""
        return calcular_kpis_tipo_evento(
            self.snap, linea_oferta=linea_oferta, modalidad=modalidad
        )

    def obtener_mart_segmentos(
        self,
        *,
        segmento_codigo: str | None = None,
        kam_id: str | None = None,
        solo_aptos: bool = False,
        limit: int = 150,
    ) -> dict[str, Any]:
        """Retorna el catálogo y detalle de los 8 segmentos de comunicaciones."""
        return consultar_segmentos_comunicaciones(
            self.snap,
            segmento_codigo=segmento_codigo,
            kam_id=kam_id,
            solo_aptos=solo_aptos,
            limit=limit,
        )
