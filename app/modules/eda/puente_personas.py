"""Construcción de la relación N:N silver_bridge_persona_empresa."""

from typing import Any

import pandas as pd

from app.modules.eda.normalizer import limpiar_texto_y_mojibake, normalizar_fecha_iso

PRIORIDAD_FUENTE: dict[str, int] = {
    "CRM": 3,
    "ASISTENCIA": 2,
    "ENCUESTA": 1,
}

PRIORIDAD_VALIDACION: dict[str, int] = {
    "CONFIRMADO_CRM": 3,
    "REPORTADO_FORMULARIO": 2,
    "INFERIDO_DOMINIO": 1,
}


def _actualizar_evidencia(
    acumulado: dict[tuple[str, str], dict[str, Any]],
    *,
    id_persona: str,
    id_empresa: str,
    cargo: str | None,
    fecha: str | None,
    fuente: str,
    validacion: str,
    es_principal_crm: bool = False,
) -> None:
    """Agrega o fusiona una evidencia de relación entre una persona y una empresa."""
    llave = (id_persona, id_empresa)
    actual = acumulado.get(llave)
    if actual is None:
        acumulado[llave] = {
            "id_persona": id_persona,
            "id_empresa": id_empresa,
            "nivel_cargo": cargo,
            "fecha_primera_evidencia": fecha,
            "fecha_ultima_evidencia": fecha,
            "fuente_relacion": fuente,
            "estado_validacion": validacion,
            "es_principal_crm": es_principal_crm,
        }
        return

    if cargo and (not actual["nivel_cargo"] or fuente == "CRM"):
        actual["nivel_cargo"] = cargo
    if fecha is not None:
        f_min = actual["fecha_primera_evidencia"]
        f_max = actual["fecha_ultima_evidencia"]
        if f_min is None or fecha < f_min:
            actual["fecha_primera_evidencia"] = fecha
        if f_max is None or fecha > f_max:
            actual["fecha_ultima_evidencia"] = fecha

    if PRIORIDAD_FUENTE[fuente] > PRIORIDAD_FUENTE[actual["fuente_relacion"]]:
        actual["fuente_relacion"] = fuente
    if (
        PRIORIDAD_VALIDACION[validacion]
        > PRIORIDAD_VALIDACION[actual["estado_validacion"]]
    ):
        actual["estado_validacion"] = validacion
    if es_principal_crm:
        actual["es_principal_crm"] = True


def _extraer_evidencias_crm(
    bronze: dict[str, pd.DataFrame],
    personas_validas: set[str],
    empresas_validas: set[str],
    acumulado: dict[tuple[str, str], dict[str, Any]],
) -> None:
    """Incorpora evidencias de vínculo desde dim_personas y fact_movimientos_crm."""
    for _, r_per in bronze["dim_personas"].iterrows():
        per_id = limpiar_texto_y_mojibake(r_per.get("id_persona"))
        emp_id = limpiar_texto_y_mojibake(r_per.get("id_empresa_principal"))
        if per_id in personas_validas and emp_id in empresas_validas:
            f_ev = normalizar_fecha_iso(
                r_per.get("fecha_afiliacion_nueva")
                or r_per.get("fecha_ultimo_evento_2026")
            )
            _actualizar_evidencia(
                acumulado,
                id_persona=str(per_id),
                id_empresa=str(emp_id),
                cargo=limpiar_texto_y_mojibake(r_per.get("nivel_cargo")),
                fecha=f_ev,
                fuente="CRM",
                validacion="CONFIRMADO_CRM",
                es_principal_crm=True,
            )

    for _, r_mov in bronze["fact_movimientos_crm"].iterrows():
        per_id = limpiar_texto_y_mojibake(r_mov.get("id_persona_contacto"))
        emp_id = limpiar_texto_y_mojibake(r_mov.get("id_empresa"))
        if per_id in personas_validas and emp_id in empresas_validas:
            _actualizar_evidencia(
                acumulado,
                id_persona=str(per_id),
                id_empresa=str(emp_id),
                cargo=None,
                fecha=normalizar_fecha_iso(r_mov.get("fecha_cierre_o_factura")),
                fuente="CRM",
                validacion="CONFIRMADO_CRM",
            )


def _extraer_evidencias_eventos_y_encuestas(
    bronze: dict[str, pd.DataFrame],
    personas_validas: set[str],
    empresas_validas: set[str],
    acumulado: dict[tuple[str, str], dict[str, Any]],
) -> None:
    """Incorpora evidencias desde asistencias a eventos y encuestas post-evento."""
    ev_fechas = {
        r_ev["id_evento"]: normalizar_fecha_iso(
            r_ev.get("fecha_inicio_evento") or r_ev.get("fecha_evento")
        )
        for _, r_ev in bronze["dim_eventos"].iterrows()
    }
    for _, r_asi in bronze["fact_asistencias"].iterrows():
        per_id = limpiar_texto_y_mojibake(r_asi.get("id_persona"))
        emp_id = limpiar_texto_y_mojibake(r_asi.get("id_empresa"))
        if per_id in personas_validas and emp_id in empresas_validas:
            f_asi = normalizar_fecha_iso(r_asi.get("fecha_evento")) or ev_fechas.get(
                r_asi.get("id_evento")
            )
            _actualizar_evidencia(
                acumulado,
                id_persona=str(per_id),
                id_empresa=str(emp_id),
                cargo=limpiar_texto_y_mojibake(r_asi.get("nivel_cargo")),
                fecha=f_asi,
                fuente="ASISTENCIA",
                validacion="REPORTADO_FORMULARIO",
            )

    for _, r_enc in bronze["fact_encuestas_satisfaccion"].iterrows():
        per_id = limpiar_texto_y_mojibake(r_enc.get("id_persona"))
        emp_id = limpiar_texto_y_mojibake(r_enc.get("id_empresa"))
        if per_id in personas_validas and emp_id in empresas_validas:
            metodo = (
                limpiar_texto_y_mojibake(r_enc.get("metodo_asignacion_empresa")) or ""
            ).lower()
            _actualizar_evidencia(
                acumulado,
                id_persona=str(per_id),
                id_empresa=str(emp_id),
                cargo=None,
                fecha=normalizar_fecha_iso(r_enc.get("fecha_encuesta")),
                fuente="ENCUESTA",
                validacion=(
                    "INFERIDO_DOMINIO" if "dominio" in metodo else "REPORTADO_FORMULARIO"
                ),
            )


def construir_bridge_persona_empresa(
    bronze: dict[str, pd.DataFrame],
    personas_validas: set[str],
    empresas_validas: set[str],
) -> tuple[pd.DataFrame, dict[tuple[str, str], int]]:
    """Construye silver_bridge_persona_empresa consolidando evidencias multi-fuente.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.
        personas_validas: Conjunto de PKs válidas en silver_dim_personas.
        empresas_validas: Conjunto de PKs válidas en silver_dim_empresas.

    Returns:
        Tupla con (df_bridge, mapa_par_a_id_vinculo).

    """
    acumulado: dict[tuple[str, str], dict[str, Any]] = {}
    _extraer_evidencias_crm(bronze, personas_validas, empresas_validas, acumulado)
    _extraer_evidencias_eventos_y_encuestas(
        bronze, personas_validas, empresas_validas, acumulado
    )

    cols_bridge = [
        "id_vinculo",
        "id_persona",
        "id_empresa",
        "nivel_cargo",
        "fecha_primera_evidencia",
        "fecha_ultima_evidencia",
        "fuente_relacion",
        "estado_validacion",
        "es_vinculo_actual",
    ]
    if not acumulado:
        return pd.DataFrame(columns=cols_bridge), {}

    df_b = pd.DataFrame(list(acumulado.values()))
    df_b["_sort_fecha"] = df_b["fecha_ultima_evidencia"].fillna("0000-00-00")
    df_b["_sort_fuente"] = df_b["fuente_relacion"].map(PRIORIDAD_FUENTE).fillna(0)
    df_b = df_b.sort_values(
        ["id_persona", "_sort_fecha", "es_principal_crm", "_sort_fuente", "id_empresa"],
        ascending=[True, False, False, False, True],
    ).reset_index(drop=True)

    df_b["es_vinculo_actual"] = ~df_b.duplicated(subset=["id_persona"], keep="first")
    df_b = (
        df_b.sort_values(["id_persona", "id_empresa"])
        .drop(columns=["es_principal_crm", "_sort_fecha", "_sort_fuente"])
        .reset_index(drop=True)
    )
    df_b.insert(0, "id_vinculo", list(range(1, len(df_b) + 1)))
    df_b = df_b[cols_bridge]

    mapa_vinculo = {
        (str(r["id_persona"]), str(r["id_empresa"])): int(r["id_vinculo"])
        for _, r in df_b.iterrows()
    }
    return df_b, mapa_vinculo
