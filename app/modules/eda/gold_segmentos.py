"""Construcción de gold_mart_segmentos_comunicaciones con resolución Habeas Data."""

from datetime import datetime
from typing import Any

import pandas as pd

from app.modules.eda.audit import BitacoraAuditoria
from app.modules.eda.bronze import guardar_tabla_medallion
from app.modules.eda.config import ConfiguracionETL

COLUMNAS_SEGMENTOS: list[str] = [
    "id_registro_segmento",
    "orden_segmento",
    "segmento_codigo",
    "segmento_nombre",
    "id_empresa",
    "id_persona",
    "rol_contacto_resuelto",
    "kam_id",
    "nivel_membresia",
    "sector_economico",
    "nombre_ciudad",
    "semaforo_riesgo_renovacion",
    "linea_2027_recomendada_ml",
    "categoria_tema_interes",
    "detalle_criterio",
    "autoriza_tratamiento_datos",
    "apto_envio_comunicaciones",
]


def _construir_mapas_habeas_y_contactos(
    silver: dict[str, pd.DataFrame],
) -> tuple[dict[str, str], dict[str, bool]]:
    """Resuelve contacto actual por empresa y mapa de autorización por persona."""
    df_br = silver["bridge_persona_empresa"]
    contacto_emp: dict[str, str] = {}
    if not df_br.empty:
        ordenado = df_br.sort_values(
            ["es_vinculo_actual", "id_vinculo"], ascending=[False, True]
        )
        for _, r_b in ordenado.iterrows():
            contacto_emp.setdefault(str(r_b["id_empresa"]), str(r_b["id_persona"]))

    aut_persona: dict[str, bool] = {}
    for df_f, col_b in (
        (silver["fact_asistencias"], "autoriza_tratamiento_datos"),
        (silver["fact_encuestas_satisfaccion"], "desea_recibir_actualizaciones"),
    ):
        for _, row in df_f[df_f["id_persona"].notna()].iterrows():
            p_id = str(row["id_persona"])
            val = row.get(col_b)
            if pd.notna(val):
                aut_persona[p_id] = aut_persona.get(p_id, False) or bool(val)

    return contacto_emp, aut_persona


def _crear_filas_desde_empresas(
    df_sub: pd.DataFrame,
    *,
    orden: int,
    codigo: str,
    nombre: str,
    contacto_emp: dict[str, str],
    aut_persona: dict[str, bool],
    col_detalle: str | None = None,
    detalle_fijo: str = "",
) -> list[dict[str, Any]]:
    """Genera registros de segmento a nivel empresa resolviendo contacto y Habeas Data."""
    filas: list[dict[str, Any]] = []
    vistas: set[str] = set()
    for _, row in df_sub.iterrows():
        emp_id = str(row["id_empresa"])
        per_id = contacto_emp.get(emp_id)
        pk = f"{codigo}::{emp_id}::{per_id or 'NA'}"
        if pk in vistas:
            continue
        vistas.add(pk)
        aut_val = aut_persona.get(per_id) if per_id else None
        det = (
            str(row[col_detalle])
            if col_detalle and pd.notna(row.get(col_detalle))
            else detalle_fijo
        )
        filas.append(
            {
                "id_registro_segmento": pk,
                "orden_segmento": orden,
                "segmento_codigo": codigo,
                "segmento_nombre": nombre,
                "id_empresa": emp_id,
                "id_persona": per_id,
                "rol_contacto_resuelto": (
                    "CONTACTO_ACTUAL_EMPRESA" if per_id else "SIN_CONTACTO_PERSONA"
                ),
                "kam_id": str(row.get("kam_id") or "KAM-UNASSIGNED"),
                "nivel_membresia": row.get("nivel_membresia"),
                "sector_economico": row.get("sector_economico"),
                "nombre_ciudad": row.get("nombre_ciudad"),
                "semaforo_riesgo_renovacion": row.get("semaforo_riesgo_renovacion"),
                "linea_2027_recomendada_ml": row.get("linea_2027_recomendada_ml"),
                "categoria_tema_interes": None,
                "detalle_criterio": det,
                "autoriza_tratamiento_datos": aut_val,
                "apto_envio_comunicaciones": bool(aut_val is True),
            }
        )
    return filas


def _limpiar_id_opt(valor: Any) -> str | None:
    """Convierte un identificador potencialmente nulo o vacío a str o None."""
    if pd.notna(valor) and str(valor).strip():
        return str(valor)
    return None


def _crear_filas_desde_interacciones(
    df_inter: pd.DataFrame,
    emp_lookup: dict[str, dict[str, Any]],
    *,
    orden: int,
    codigo: str,
    nombre: str,
    rol_defecto: str,
    col_aut: str,
    col_tema: str | None = None,
    prefijo_detalle: str = "",
) -> list[dict[str, Any]]:
    """Genera registros de segmento a partir de asistencias o encuestas Gold."""
    filas: list[dict[str, Any]] = []
    vistas: set[str] = set()
    for _, row in df_inter.iterrows():
        emp_id = _limpiar_id_opt(row.get("id_empresa"))
        per_id = _limpiar_id_opt(row.get("id_persona"))
        if emp_id is None and per_id is None:
            continue
        pk = f"{codigo}::{emp_id or 'NA'}::{per_id or 'NA'}"
        if pk in vistas:
            continue
        vistas.add(pk)

        info = emp_lookup.get(emp_id, {}) if emp_id else {}
        aut_val = None if pd.isna(row.get(col_aut)) else bool(row.get(col_aut))
        tema_val = (
            str(row[col_tema]) if col_tema and pd.notna(row.get(col_tema)) else None
        )
        filas.append(
            {
                "id_registro_segmento": pk,
                "orden_segmento": orden,
                "segmento_codigo": codigo,
                "segmento_nombre": nombre,
                "id_empresa": emp_id,
                "id_persona": per_id,
                "rol_contacto_resuelto": (
                    rol_defecto if per_id else "SIN_CONTACTO_PERSONA"
                ),
                "kam_id": str(info.get("kam_id") or "KAM-UNASSIGNED"),
                "nivel_membresia": info.get("nivel_membresia"),
                "sector_economico": info.get("sector_economico"),
                "nombre_ciudad": info.get("nombre_ciudad")
                or row.get("nombre_ciudad_asistente")
                or row.get("nombre_ciudad_encuesta"),
                "semaforo_riesgo_renovacion": info.get("semaforo_riesgo_renovacion"),
                "linea_2027_recomendada_ml": info.get("linea_2027_recomendada_ml"),
                "categoria_tema_interes": tema_val,
                "detalle_criterio": (
                    f"{prefijo_detalle}: {tema_val}" if tema_val else prefijo_detalle
                ),
                "autoriza_tratamiento_datos": aut_val,
                "apto_envio_comunicaciones": bool(aut_val is True),
            }
        )
    return filas


def _generar_segmentos_empresa(
    activas: pd.DataFrame,
    contacto_emp: dict[str, str],
    aut_persona: dict[str, bool],
    fecha_corte: str,
) -> dict[int, list[dict[str, Any]]]:
    """Genera los segmentos corporativos 1, 2, 6 y 8."""
    dias_af = (
        pd.Timestamp(fecha_corte)
        - pd.to_datetime(activas["fecha_afiliacion_actual"], errors="coerce")
    ).dt.days
    return {
        1: _crear_filas_desde_empresas(
            activas[activas["asistencias_ultimo_trimestre"] == 0],
            orden=1,
            codigo="AFILIADOS_SIN_PARTICIPACION",
            nombre="1. Afiliados que no participan",
            contacto_emp=contacto_emp,
            aut_persona=aut_persona,
            col_detalle="linea_2027_recomendada_ml",
            detalle_fijo="Sin asistencias en el último trimestre",
        ),
        2: _crear_filas_desde_empresas(
            activas[activas["alerta_vencimiento_90d"]].sort_values(
                "puntaje_riesgo_heuristico", ascending=False
            ),
            orden=2,
            codigo="VENCIMIENTOS_PROXIMOS_90D",
            nombre="2. Vencimientos próximos (90 días)",
            contacto_emp=contacto_emp,
            aut_persona=aut_persona,
            col_detalle="tramo_vencimiento",
            detalle_fijo="Membresía próxima a vencer <= 90 días",
        ),
        6: _crear_filas_desde_empresas(
            activas[activas["alerta_monocontacto"]],
            orden=6,
            codigo="AFILIADOS_UN_SOLO_CONTACTO",
            nombre="6. Afiliados de un solo contacto",
            contacto_emp=contacto_emp,
            aut_persona=aut_persona,
            detalle_fijo="Empresa activa donde participa una única persona",
        ),
        8: _crear_filas_desde_empresas(
            activas[dias_af.between(0, 90, inclusive="both")],
            orden=8,
            codigo="NUEVOS_AFILIADOS_ONBOARDING",
            nombre="8. Nuevos afiliados (< 90 días)",
            contacto_emp=contacto_emp,
            aut_persona=aut_persona,
            col_detalle="fecha_afiliacion_actual",
            detalle_fijo="Afiliado reciente (< 90 días)",
        ),
    }


def _generar_segmentos_interaccion(
    emp_lookup: dict[str, dict[str, Any]],
    df_asist_bi: pd.DataFrame,
    df_enc_bi: pd.DataFrame,
) -> dict[int, list[dict[str, Any]]]:
    """Genera los segmentos de personas e interacciones 3, 4, 5 y 7."""
    enc_det = df_enc_bi[
        (df_enc_bi["nivel_satisfaccion_1_5"] == "BAJA")
        | (df_enc_bi["categoria_nps_0_10"] == "DETRACTOR")
    ]
    enc_prom = df_enc_bi[
        (df_enc_bi["categoria_nps_0_10"] == "PROMOTOR")
        | (
            df_enc_bi["categoria_nps_0_10"].isna()
            & (df_enc_bi["promedio_respuesta_1_5"] == 5.0)
        )
    ].copy()
    enc_prom["_origen_prom"] = enc_prom["categoria_nps_0_10"].fillna(
        "CANDIDATO_LIKERT_5_0_SIN_NPS_0_10"
    )

    s7_enc = _crear_filas_desde_interacciones(
        df_enc_bi[df_enc_bi["categoria_tema_nlp"].notna()],
        emp_lookup,
        orden=7,
        codigo="INTERES_POR_TEMA_Y_LINEA",
        nombre="7. Interés por tema y por línea",
        rol_defecto="ENCUESTADO",
        col_aut="desea_recibir_actualizaciones",
        col_tema="categoria_tema_nlp",
        prefijo_detalle="Tema solicitado en encuesta",
    )
    s7_lin = _crear_filas_desde_interacciones(
        df_asist_bi[df_asist_bi["id_empresa"].notna()],
        emp_lookup,
        orden=7,
        codigo="INTERES_POR_TEMA_Y_LINEA",
        nombre="7. Interés por tema y por línea",
        rol_defecto="ASISTENTE",
        col_aut="autoriza_tratamiento_datos",
        col_tema="linea_oferta_2027",
        prefijo_detalle="Participación activa en línea 2027",
    )
    vistas_s7 = {r["id_registro_segmento"] for r in s7_enc}

    return {
        3: _crear_filas_desde_interacciones(
            enc_det,
            emp_lookup,
            orden=3,
            codigo="DETRACTORES_RECIENTES",
            nombre="3. Detractores recientes",
            rol_defecto="ENCUESTADO",
            col_aut="desea_recibir_actualizaciones",
            col_tema="promedio_respuesta_1_5",
            prefijo_detalle="Calificación baja (<3.75) o Detractor NPS",
        ),
        4: _crear_filas_desde_interacciones(
            enc_prom,
            emp_lookup,
            orden=4,
            codigo="PROMOTORES_TESTIMONIOS",
            nombre="4. Promotores para testimonios",
            rol_defecto="ENCUESTADO",
            col_aut="desea_recibir_actualizaciones",
            col_tema="_origen_prom",
            prefijo_detalle="Promotor identificado",
        ),
        5: _crear_filas_desde_interacciones(
            df_asist_bi[df_asist_bi["tipo_asistencia"] != "Afiliado"],
            emp_lookup,
            orden=5,
            codigo="ASISTENTES_NO_AFILIADOS_LEADS",
            nombre="5. Asistentes no afiliados (Leads)",
            rol_defecto="ASISTENTE",
            col_aut="autoriza_tratamiento_datos",
            col_tema="linea_oferta_2027",
            prefijo_detalle="Asistente no afiliado en línea",
        ),
        7: s7_enc + [r for r in s7_lin if r["id_registro_segmento"] not in vistas_s7],
    }


def construir_mart_segmentos_comunicaciones(
    silver: dict[str, pd.DataFrame],
    df_emp_360: pd.DataFrame,
    df_asist_bi: pd.DataFrame,
    df_enc_bi: pd.DataFrame,
    *,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye gold_mart_segmentos_comunicaciones y exporta los 8 CSV de campaña."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    contacto_emp, aut_persona = _construir_mapas_habeas_y_contactos(silver)
    emp_lookup: dict[str, dict[str, Any]] = {
        str(r["id_empresa"]): {str(k): v for k, v in r.to_dict().items()}
        for _, r in df_emp_360.iterrows()
    }
    activas = df_emp_360[df_emp_360["tipo_relacion_actho"] == "AFILIADO_ACTIVO"].copy()

    segs = {
        **_generar_segmentos_empresa(activas, contacto_emp, aut_persona, cfg.fecha_corte),
        **_generar_segmentos_interaccion(emp_lookup, df_asist_bi, df_enc_bi),
    }

    archivos = (
        (1, "1_afiliados_que_no_participan.csv"),
        (2, "2_vencimientos_proximos_90d.csv"),
        (3, "3_detractores_recientes.csv"),
        (4, "4_promotores_testimonios.csv"),
        (5, "5_asistentes_no_afiliados_leads.csv"),
        (6, "6_afiliados_un_solo_contacto.csv"),
        (7, "7_interes_por_tema_y_linea.csv"),
        (8, "8_nuevos_afiliados_onboarding.csv"),
    )
    dir_seg = cfg.gold_dir / "segmentos_comunicaciones"
    dir_seg.mkdir(parents=True, exist_ok=True)

    todas: list[dict[str, Any]] = []
    for num, nom_csv in archivos:
        lista = segs[num]
        df_ind = (
            pd.DataFrame(lista)[COLUMNAS_SEGMENTOS]
            if lista
            else pd.DataFrame(columns=COLUMNAS_SEGMENTOS)
        )
        df_ind.to_csv(dir_seg / nom_csv, index=False, encoding="utf-8-sig")
        todas.extend(lista)

    df_mart_seg = (
        pd.DataFrame(todas)[COLUMNAS_SEGMENTOS]
        if todas
        else pd.DataFrame(columns=COLUMNAS_SEGMENTOS)
    )
    guardar_tabla_medallion(df_mart_seg, cfg.gold_dir, "mart_segmentos_comunicaciones")
    bitacora.registrar_carga(
        "silver+gold -> gold/mart_segmentos_comunicaciones",
        t0,
        leidos=len(df_emp_360) + len(df_asist_bi) + len(df_enc_bi),
        proc=len(df_mart_seg),
        ins=len(df_mart_seg),
        act=0,
    )
    return df_mart_seg
