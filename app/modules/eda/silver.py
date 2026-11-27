"""Transformaciones de la capa Silver normalizada (13 entidades 3NF y Hechos)."""

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from app.modules.eda.audit import BitacoraAuditoria, filtrar_registros_rechazados
from app.modules.eda.bronze import (
    guardar_tabla_medallion,
    homologar_kam_id,
    homologar_kam_opcional,
)
from app.modules.eda.config import ConfiguracionETL
from app.modules.eda.geografia import (
    CatalogoGeografico,
    construir_catalogo_geografico,
    extraer_ciudad_sede_evento,
)
from app.modules.eda.membresias import (
    _homologar_par_categoria,
    construir_catalogo_y_membresias,
)
from app.modules.eda.normalizer import (
    limpiar_texto_y_mojibake,
    normalizar_booleano,
    normalizar_fecha_iso,
    normalizar_sector,
)
from app.modules.eda.puente_personas import construir_bridge_persona_empresa


def _a_int64_nullable(serie: pd.Series) -> pd.Series:
    """Convierte una serie numérica o con nulos al tipo entero nullable Int64."""
    return pd.to_numeric(serie, errors="coerce").round().astype("Int64")


def _limpiar_archivos_legado_silver(cfg: ConfiguracionETL) -> None:
    """Elimina archivos obsoletos de versiones previas en la carpeta Silver."""
    for ext in ("csv", "parquet"):
        legado = cfg.silver_dir / f"dim_empresas_scd2.{ext}"
        if legado.exists():
            legado.unlink()


def _persistir_geografia(
    bronze: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> CatalogoGeografico:
    """Construye y persiste las 3 tablas geográficas (país, departamento, ciudad)."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    geo = construir_catalogo_geografico(bronze)
    guardar_tabla_medallion(geo.dim_pais, cfg.silver_dir, "dim_pais")
    guardar_tabla_medallion(geo.dim_departamento, cfg.silver_dir, "dim_departamento")
    guardar_tabla_medallion(geo.dim_ciudad, cfg.silver_dir, "dim_ciudad")

    bitacora.registrar_carga(
        "bronze/geografia -> silver/dim_pais_departamento_ciudad",
        t0,
        leidos=len(bronze["dim_empresas"]),
        proc=len(geo.dim_ciudad),
        ins=len(geo.dim_pais) + len(geo.dim_departamento) + len(geo.dim_ciudad),
        act=0,
    )
    return geo


def _procesar_dim_kams(
    bronze: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye silver_dim_kams limpia y separa métricas precalculadas a Audit."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_orig = bronze["dim_kams"].copy()
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
        if c in df_orig.columns
    ]
    guardar_tabla_medallion(
        df_orig[cols_metricas], cfg.audit_dir, "audit_metricas_origen_kams"
    )

    kam_hom = df_orig["kam_id"].apply(lambda v: homologar_kam_id(v, cfg))
    df_kams = pd.DataFrame(
        {
            "kam_id": kam_hom,
            "responsable_nombre": df_orig["responsable_nombre"].apply(
                lambda v: limpiar_texto_y_mojibake(v) or "No especificado"
            ),
            "tiene_seguimiento_eventos": df_orig["tiene_seguimiento_eventos"]
            .fillna(False)
            .astype(bool),
        }
    )
    if cfg.kam_sin_asignar_id not in set(df_kams["kam_id"]):
        fila_unassigned = pd.DataFrame(
            [
                {
                    "kam_id": cfg.kam_sin_asignar_id,
                    "responsable_nombre": "Corporativo / Sin asignar",
                    "tiene_seguimiento_eventos": False,
                }
            ]
        )
        df_kams = pd.concat([df_kams, fila_unassigned], ignore_index=True)

    df_kams, rech = filtrar_registros_rechazados(
        df_kams, "dim_kams", ["kam_id"], "dim_kams.csv", bitacora
    )
    guardar_tabla_medallion(df_kams, cfg.silver_dir, "dim_kams")
    bitacora.registrar_calidad(
        "dim_kams",
        "kam_id",
        tipo_inc="HOMOLOGACION_Y_LIMPIEZA_ATRIBUTOS_REDUNDANTES",
        val_orig="Sin asignar (cuenta ACTHO) y columnas derivadas eliminadas",
        val_corr=cfg.kam_sin_asignar_id,
        estado="CORREGIDO_HOMOLOGADO",
        cant=1,
    )
    bitacora.registrar_carga(
        "bronze/dim_kams -> silver/dim_kams",
        t0,
        leidos=len(df_orig),
        proc=len(df_kams),
        ins=len(df_kams),
        act=1,
        rech=rech,
    )
    return df_kams


def _procesar_empresas_y_membresias(
    bronze: dict[str, pd.DataFrame],
    geo: CatalogoGeografico,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[tuple[str, str], int]]:
    """Construye dim_empresas, dim_catalogo_membresia y membresias en Silver."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_orig = bronze["dim_empresas"].copy()
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
        if c in df_orig.columns
    ]
    guardar_tabla_medallion(
        df_orig[cols_metricas], cfg.audit_dir, "audit_metricas_origen_empresas"
    )

    cnt_sin_asig = int(df_orig["kam_id"].isin(cfg.valores_origen_sin_asignar).sum())
    ciudades_fk = [
        geo.resolver_id_ciudad(
            r.get("ciudad"), r.get("region_departamento"), r.get("pais")
        )
        for _, r in df_orig.iterrows()
    ]

    df_emp = pd.DataFrame(
        {
            "id_empresa": df_orig["id_empresa"].apply(limpiar_texto_y_mojibake),
            "id_registro_crm": df_orig["id_registro_crm"].apply(limpiar_texto_y_mojibake),
            "kam_id": df_orig["kam_id"].apply(lambda v: homologar_kam_id(v, cfg)),
            "id_ciudad_empresa": pd.Series(ciudades_fk, dtype="Int64"),
            "es_empresa_activa": df_orig["es_empresa_activa"].eq(True),
            "sector_economico": df_orig["sector_economico"].apply(normalizar_sector),
            "subsector_economico": df_orig["subsector_economico"].apply(
                limpiar_texto_y_mojibake
            ),
            "tamano_empresa": df_orig["tamano_empresa"].apply(limpiar_texto_y_mojibake),
            "rango_empleados": df_orig["rango_empleados"].apply(limpiar_texto_y_mojibake),
            "porcentaje_mujeres_num": pd.to_numeric(
                df_orig["porcentaje_mujeres_num"], errors="coerce"
            ),
            "fecha_ultima_actividad_crm": df_orig["fecha_ultima_actividad"].apply(
                normalizar_fecha_iso
            ),
            "es_independiente": df_orig["es_independiente"].apply(normalizar_booleano),
            "es_registro_prueba": df_orig["es_registro_prueba"].apply(
                normalizar_booleano
            ),
            "bloqueado_crm": df_orig["bloqueado_crm"].apply(normalizar_booleano),
            "vinculado_comunidades": df_orig["vinculado_comunidades"].apply(
                normalizar_booleano
            ),
            "pilar_hr_estrategico": df_orig["pilar_hr_estrategico"].apply(
                normalizar_booleano
            ),
            "pilar_mas_que_salario": df_orig["pilar_mas_que_salario"].apply(
                normalizar_booleano
            ),
            "pilar_talento_que_elige": df_orig["pilar_talento_que_elige"].apply(
                normalizar_booleano
            ),
            "pilar_gente_que_crece": df_orig["pilar_gente_que_crece"].apply(
                normalizar_booleano
            ),
            "comunidad_mujeres_hr": df_orig["comunidad_mujeres_hr"].apply(
                normalizar_booleano
            ),
            "es_influenciador": df_orig["es_influenciador"].apply(normalizar_booleano),
        }
    )
    df_emp, rech = filtrar_registros_rechazados(
        df_emp, "dim_empresas", ["id_empresa"], "dim_empresas.csv", bitacora
    )
    guardar_tabla_medallion(df_emp, cfg.silver_dir, "dim_empresas")

    t1 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dim_cat, df_mem, mapa_cat = construir_catalogo_y_membresias(bronze, cfg, bitacora)
    df_mem = df_mem[df_mem["id_empresa"].isin(set(df_emp["id_empresa"]))].reset_index(
        drop=True
    )
    df_mem, rech_mem = filtrar_registros_rechazados(
        df_mem, "membresias", ["id_membresia"], "dim_empresas.csv", bitacora
    )
    guardar_tabla_medallion(dim_cat, cfg.silver_dir, "dim_catalogo_membresia")
    guardar_tabla_medallion(df_mem, cfg.silver_dir, "membresias")

    bitacora.registrar_carga(
        "bronze/dim_empresas -> silver/dim_empresas",
        t0,
        leidos=len(df_orig),
        proc=len(df_emp),
        ins=len(df_emp),
        act=cnt_sin_asig,
        rech=rech,
    )
    bitacora.registrar_carga(
        "bronze/dim_empresas -> silver/membresias (+catalogo)",
        t1,
        leidos=len(df_orig),
        proc=len(df_mem),
        ins=len(df_mem) + len(dim_cat),
        act=0,
        rech=rech_mem,
    )
    return df_emp, dim_cat, df_mem, mapa_cat


def _procesar_dim_eventos(
    bronze: dict[str, pd.DataFrame],
    geo: CatalogoGeografico,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye silver_dim_eventos eliminando fecha_evento redundante."""
    t1 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_ev_orig = bronze["dim_eventos"].copy()
    f_ini = df_ev_orig["fecha_inicio_evento"].apply(normalizar_fecha_iso)
    f_ini_final = f_ini.fillna(df_ev_orig["fecha_evento"].apply(normalizar_fecha_iso))
    f_fin_final = (
        df_ev_orig["fecha_fin_evento"].apply(normalizar_fecha_iso).fillna(f_ini_final)
    )
    ciudades_ev = [
        extraer_ciudad_sede_evento(r.get("nombre_evento"), r.get("modalidad"), geo)
        for _, r in df_ev_orig.iterrows()
    ]

    df_ev = pd.DataFrame(
        {
            "id_evento": pd.to_numeric(df_ev_orig["id_evento"], errors="coerce"),
            "id_ciudad_evento": pd.Series(ciudades_ev, dtype="Int64"),
            "nombre_evento": df_ev_orig["nombre_evento"].apply(limpiar_texto_y_mojibake),
            "fecha_inicio_evento": f_ini_final,
            "fecha_fin_evento": f_fin_final,
            "linea_oferta_2027": df_ev_orig["linea_oferta_2027"].apply(
                lambda v: limpiar_texto_y_mojibake(v) or "Sin clasificar"
            ),
            "experiencia_detalle": df_ev_orig["experiencia_detalle"].apply(
                limpiar_texto_y_mojibake
            ),
            "modalidad": df_ev_orig["modalidad"].apply(
                lambda v: limpiar_texto_y_mojibake(v) or "Virtual"
            ),
        }
    )
    df_ev, rech_ev = filtrar_registros_rechazados(
        df_ev, "dim_eventos", ["id_evento"], "dim_eventos.csv", bitacora
    )
    df_ev["id_evento"] = df_ev["id_evento"].astype(int)
    guardar_tabla_medallion(df_ev, cfg.silver_dir, "dim_eventos")
    bitacora.registrar_carga(
        "bronze/dim_eventos -> silver/dim_eventos",
        t1,
        leidos=len(df_ev_orig),
        proc=len(df_ev),
        ins=len(df_ev),
        act=0,
        rech=rech_ev,
    )
    return df_ev


def _procesar_personas_y_puente(
    bronze: dict[str, pd.DataFrame],
    df_emp: pd.DataFrame,
    geo: CatalogoGeografico,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, str], int]]:
    """Construye silver_dim_personas y silver_bridge_persona_empresa."""
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

    df_per = pd.DataFrame(
        {
            "id_persona": df_per_orig["id_persona"].apply(limpiar_texto_y_mojibake),
            "id_ciudad_persona": pd.Series(
                [geo.resolver_id_ciudad(v) for v in df_per_orig["ciudad"]],
                dtype="Int64",
            ),
            "nivel_cargo_actual": df_per_orig["nivel_cargo"].apply(
                limpiar_texto_y_mojibake
            ),
        }
    )
    df_per, rech_per = filtrar_registros_rechazados(
        df_per, "dim_personas", ["id_persona"], "dim_personas.csv", bitacora
    )
    guardar_tabla_medallion(df_per, cfg.silver_dir, "dim_personas")
    bitacora.registrar_carga(
        "bronze/dim_personas -> silver/dim_personas",
        t0,
        leidos=len(df_per_orig),
        proc=len(df_per),
        ins=len(df_per),
        act=0,
        rech=rech_per,
    )

    t_br = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_bridge, mapa_vinculo = construir_bridge_persona_empresa(
        bronze,
        personas_validas=set(df_per["id_persona"]),
        empresas_validas=set(df_emp["id_empresa"]),
    )
    guardar_tabla_medallion(df_bridge, cfg.silver_dir, "bridge_persona_empresa")
    bitacora.registrar_carga(
        "bronze/multi -> silver/bridge_persona_empresa",
        t_br,
        leidos=len(df_per),
        proc=len(df_bridge),
        ins=len(df_bridge),
        act=0,
    )
    return df_per, df_bridge, mapa_vinculo


def _guardar_audit_metricas_eventos(
    df_ev_orig: pd.DataFrame,
    df_asist_silver: pd.DataFrame,
    cfg: ConfiguracionETL,
) -> None:
    """Concilia métricas de eventos de origen contra silver_fact_asistencias."""
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
    guardar_tabla_medallion(df_audit_ev, cfg.audit_dir, "audit_metricas_origen_eventos")


def _procesar_fact_asistencias(
    bronze: dict[str, pd.DataFrame],
    geo: CatalogoGeografico,
    mapa_vinculo: dict[tuple[str, str], int],
    kams_validos: set[str],
    *,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye silver_fact_asistencias con id_vinculo y sin atributos redundantes."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_orig = bronze["fact_asistencias"].copy()

    per_limpios = df_orig["id_persona"].apply(limpiar_texto_y_mojibake)
    emp_limpios = df_orig["id_empresa"].apply(limpiar_texto_y_mojibake)
    vinculos = [
        mapa_vinculo.get((str(p), str(e))) if (p and e) else None
        for p, e in zip(per_limpios, emp_limpios)
    ]
    kams_opt = [
        k if (k := homologar_kam_opcional(v, cfg)) in kams_validos else None
        for v in df_orig["kam_id"]
    ]
    tipo_asist = np.where(
        df_orig["es_afiliado"].eq(True), "Afiliado", "No Afiliado / Invitado"
    )

    df_asist = pd.DataFrame(
        {
            "id_asistencia": df_orig["id_asistencia"].apply(limpiar_texto_y_mojibake),
            "id_evento": pd.to_numeric(df_orig["id_evento"], errors="coerce"),
            "id_persona": per_limpios,
            "id_empresa": emp_limpios,
            "id_vinculo": pd.Series(vinculos, dtype="Int64"),
            "kam_id": kams_opt,
            "id_ciudad_asistente": pd.Series(
                [geo.resolver_id_ciudad(v) for v in df_orig["ciudad_evento"]],
                dtype="Int64",
            ),
            "nivel_cargo_evento": df_orig["nivel_cargo"].apply(limpiar_texto_y_mojibake),
            "tipo_asistencia": tipo_asist,
            "cantidad_inscritos": _a_int64_nullable(df_orig["cantidad_inscritos"]),
            "tiene_costo": df_orig["tiene_costo"].apply(normalizar_booleano),
            "autoriza_tratamiento_datos": df_orig["autoriza_tratamiento_datos"].apply(
                normalizar_booleano
            ),
        }
    )
    df_asist, rech = filtrar_registros_rechazados(
        df_asist,
        "fact_asistencias",
        ["id_asistencia"],
        "fact_asistencias.csv",
        bitacora,
    )
    df_asist["id_evento"] = df_asist["id_evento"].astype(int)
    guardar_tabla_medallion(df_asist, cfg.silver_dir, "fact_asistencias")
    bitacora.registrar_carga(
        "bronze/fact_asistencias -> silver/fact_asistencias",
        t0,
        leidos=len(df_orig),
        proc=len(df_asist),
        ins=len(df_asist),
        act=0,
        rech=rech,
    )
    _guardar_audit_metricas_eventos(bronze["dim_eventos"], df_asist, cfg)
    return df_asist


def _normalizar_tipo_encuesta(valor: Any) -> str:
    """Homologa la tipología de encuesta entre POST_EVENTO y ENCUESTA_90_DIAS."""
    txt = (limpiar_texto_y_mojibake(valor) or "").upper()
    return "ENCUESTA_90_DIAS" if "90" in txt else "POST_EVENTO"


def _procesar_fact_encuestas(
    bronze: dict[str, pd.DataFrame],
    geo: CatalogoGeografico,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye silver_fact_encuestas_satisfaccion sin duplicar promedios."""
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_enc_orig = bronze["fact_encuestas_satisfaccion"].copy()

    ev_col = (
        _a_int64_nullable(df_enc_orig["id_evento"])
        if "id_evento" in df_enc_orig.columns
        else pd.Series([pd.NA] * len(df_enc_orig), dtype="Int64")
    )
    nps_col = (
        _a_int64_nullable(df_enc_orig["pregunta_recomendacion_nps_0_10"])
        if "pregunta_recomendacion_nps_0_10" in df_enc_orig.columns
        else pd.Series([pd.NA] * len(df_enc_orig), dtype="Int64")
    )
    tipo_col = (
        df_enc_orig["tipo_encuesta"].apply(_normalizar_tipo_encuesta)
        if "tipo_encuesta" in df_enc_orig.columns
        else pd.Series(["POST_EVENTO"] * len(df_enc_orig))
    )

    df_enc = pd.DataFrame(
        {
            "id_respuesta": df_enc_orig["id_respuesta"].apply(limpiar_texto_y_mojibake),
            "id_evento": ev_col,
            "id_persona": df_enc_orig["id_persona"].apply(limpiar_texto_y_mojibake),
            "id_empresa": df_enc_orig["id_empresa"].apply(limpiar_texto_y_mojibake),
            "id_ciudad_encuesta": pd.Series(
                [geo.resolver_id_ciudad(v) for v in df_enc_orig["ciudad"]],
                dtype="Int64",
            ),
            "fecha_encuesta": df_enc_orig["fecha_encuesta"].apply(normalizar_fecha_iso),
            "modalidad_encuesta": df_enc_orig["modalidad_encuesta"].apply(
                lambda v: limpiar_texto_y_mojibake(v) or "Virtual"
            ),
            "tipo_encuesta": tipo_col,
            "duracion_segundos": _a_int64_nullable(df_enc_orig["duracion_segundos"]),
            "calif_locacion_o_plataforma": _a_int64_nullable(
                df_enc_orig["calif_locacion_o_plataforma"]
            ),
            "calif_convocatoria_publicidad": _a_int64_nullable(
                df_enc_orig["calif_convocatoria_publicidad"]
            ),
            "calif_conferencistas": _a_int64_nullable(
                df_enc_orig["calif_conferencistas"]
            ),
            "calif_relevancia_temas": _a_int64_nullable(
                df_enc_orig["calif_relevancia_temas"]
            ),
            "pregunta_recomendacion_nps_0_10": nps_col,
            "temarios_sugeridos": df_enc_orig["temarios_sugeridos"].apply(
                limpiar_texto_y_mojibake
            ),
            "desea_recibir_actualizaciones": df_enc_orig[
                "desea_recibir_actualizaciones"
            ].apply(normalizar_booleano),
        }
    )
    df_enc, rech_enc = filtrar_registros_rechazados(
        df_enc,
        "fact_encuestas_satisfaccion",
        ["id_respuesta"],
        "fact_encuestas_satisfaccion.csv",
        bitacora,
    )
    guardar_tabla_medallion(df_enc, cfg.silver_dir, "fact_encuestas_satisfaccion")
    bitacora.registrar_carga(
        "bronze/fact_encuestas_satisfaccion -> silver/fact_encuestas_satisfaccion",
        t0,
        leidos=len(df_enc_orig),
        proc=len(df_enc),
        ins=len(df_enc),
        act=0,
        rech=rech_enc,
    )
    return df_enc


def _procesar_fact_movimientos_crm(
    bronze: dict[str, pd.DataFrame],
    df_mem: pd.DataFrame,
    mapa_cat: dict[tuple[str, str], int],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye silver_fact_movimientos_crm con id_membresia opcional."""
    t1 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_mov_orig = bronze["fact_movimientos_crm"].copy()
    ult_mem = (
        df_mem.drop_duplicates(subset=["id_empresa"], keep="last")
        .set_index("id_empresa")["id_membresia"]
        .to_dict()
        if not df_mem.empty
        else {}
    )

    mem_fks: list[str | None] = []
    cat_fks: list[int | None] = []
    estados_mov: list[str] = []
    for _, m_row in df_mov_orig.iterrows():
        t_mov = limpiar_texto_y_mojibake(m_row.get("tipo_movimiento")) or "Movimiento"
        fact = bool(m_row.get("es_cierre_facturado", False))
        emp_id = limpiar_texto_y_mojibake(m_row.get("id_empresa")) or ""
        mem_fks.append(
            None if (t_mov == "Trato en Estado" or not fact) else ult_mem.get(emp_id)
        )
        cat_fks.append(
            mapa_cat.get(_homologar_par_categoria(None, m_row.get("nivel_membresia")))
        )
        estados_mov.append(
            "Cerrado Facturado" if fact else "En gestión / Oportunidad CRM"
        )

    df_mov = pd.DataFrame(
        {
            "id_movimiento": [f"MOV-{idx:04d}" for idx in range(1, len(df_mov_orig) + 1)],
            "id_empresa": df_mov_orig["id_empresa"].apply(limpiar_texto_y_mojibake),
            "id_membresia": mem_fks,
            "kam_id": df_mov_orig["kam_id"].apply(lambda v: homologar_kam_id(v, cfg)),
            "id_persona_contacto": df_mov_orig["id_persona_contacto"].apply(
                limpiar_texto_y_mojibake
            ),
            "id_cat_membresia_movimiento": pd.Series(cat_fks, dtype="Int64"),
            "tipo_movimiento": df_mov_orig["tipo_movimiento"].apply(
                lambda v: limpiar_texto_y_mojibake(v) or "Movimiento CRM"
            ),
            "estado_movimiento_crm": estados_mov,
            "es_cierre_facturado": df_mov_orig["es_cierre_facturado"].eq(True),
            "fecha_cierre_o_factura": df_mov_orig["fecha_cierre_o_factura"].apply(
                normalizar_fecha_iso
            ),
            "fecha_expiracion_afiliacion": df_mov_orig[
                "fecha_expiracion_afiliacion"
            ].apply(normalizar_fecha_iso),
        }
    )
    df_mov, rech_mov = filtrar_registros_rechazados(
        df_mov,
        "fact_movimientos_crm",
        ["id_movimiento"],
        "fact_movimientos_crm.csv",
        bitacora,
    )
    guardar_tabla_medallion(df_mov, cfg.silver_dir, "fact_movimientos_crm")
    bitacora.registrar_carga(
        "bronze/fact_movimientos_crm -> silver/fact_movimientos_crm",
        t1,
        leidos=len(df_mov_orig),
        proc=len(df_mov),
        ins=len(df_mov),
        act=len(df_mov),
        rech=rech_mov,
    )
    return df_mov


def procesar_capa_silver(
    bronze: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> dict[str, pd.DataFrame]:
    """Ejecuta la construcción completa de las 13 entidades de la capa Silver."""
    _limpiar_archivos_legado_silver(cfg)
    geo = _persistir_geografia(bronze, cfg, bitacora)
    df_kams = _procesar_dim_kams(bronze, cfg, bitacora)
    df_emp, dim_cat, df_mem, mapa_cat = _procesar_empresas_y_membresias(
        bronze, geo, cfg, bitacora
    )
    df_per, df_bridge, mapa_vinculo = _procesar_personas_y_puente(
        bronze, df_emp, geo, cfg, bitacora
    )
    df_ev = _procesar_dim_eventos(bronze, geo, cfg, bitacora)
    df_asist = _procesar_fact_asistencias(
        bronze,
        geo,
        mapa_vinculo,
        set(df_kams["kam_id"]),
        cfg=cfg,
        bitacora=bitacora,
    )
    df_enc = _procesar_fact_encuestas(bronze, geo, cfg, bitacora)
    df_mov = _procesar_fact_movimientos_crm(bronze, df_mem, mapa_cat, cfg, bitacora)

    return {
        "dim_pais": geo.dim_pais,
        "dim_departamento": geo.dim_departamento,
        "dim_ciudad": geo.dim_ciudad,
        "dim_kams": df_kams,
        "dim_empresas": df_emp,
        "dim_catalogo_membresia": dim_cat,
        "membresias": df_mem,
        "dim_personas": df_per,
        "bridge_persona_empresa": df_bridge,
        "dim_eventos": df_ev,
        "fact_asistencias": df_asist,
        "fact_encuestas_satisfaccion": df_enc,
        "fact_movimientos_crm": df_mov,
    }
