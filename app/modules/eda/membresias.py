"""Construcción de silver_dim_catalogo_membresia y silver_membresias (ciclos reales)."""

from typing import Any

import pandas as pd

from app.modules.eda.audit import BitacoraAuditoria
from app.modules.eda.bronze import homologar_kam_opcional
from app.modules.eda.config import ConfiguracionETL
from app.modules.eda.normalizer import limpiar_texto_y_mojibake, normalizar_fecha_iso

MAPA_TIPO_A_SEGMENTO: dict[str, str] = {
    "empresa": "Corporativa / Empresa",
    "corporativa estándar": "Corporativa / Empresa",
    "corporativa estandar": "Corporativa / Empresa",
    "corporativa premium": "Corporativa / Empresa",
    "consultoras": "Consultora / Vendor",
    "consultor/vendor estándar": "Consultora / Vendor",
    "consultor/vendor estandar": "Consultora / Vendor",
    "consultor/vendor premium": "Consultora / Vendor",
    "persona natural": "Persona Natural",
    "personal premium": "Persona Natural",
    "personal estándar": "Persona Natural",
    "personal estandar": "Persona Natural",
    "jóvenes talentos / estudiantes": "Persona Natural",
    "universidades": "Universidad",
}

MAPA_CAT_A_NIVEL: dict[str, str] = {
    "estándar": "Estándar",
    "estandar": "Estándar",
    "empresas": "Estándar",
    "consultoras": "Estándar",
    "persona natural": "Estándar",
    "premium": "Premium",
    "plus": "Premium",
    "elite": "Elite",
    "personal": "Personal",
    "estándar colaborador": "Estándar Colaborador",
    "estandar colaborador": "Estándar Colaborador",
}


def _sanear_fecha_membresia(
    valor: Any,
    anio_maximo: int,
    anomalias: list[str],
) -> str | None:
    """Normaliza una fecha ISO y descarta años corruptos fuera de rango razonable."""
    iso = normalizar_fecha_iso(valor)
    if iso is None:
        return None
    anio = int(iso[:4])
    if anio < 1950 or anio > anio_maximo:
        anomalias.append(iso)
        return None
    return iso


def _homologar_par_categoria(
    segmento_raw: Any,
    nivel_raw: Any,
    tipo_orig: Any = None,
    cat_orig: Any = None,
) -> tuple[str, str]:
    """Homologa el par (segmento_membresia, nivel_membresia) sin valores nulos."""
    seg = limpiar_texto_y_mojibake(segmento_raw)
    if not seg or seg.lower() == "sin clasificar":
        t_clean = (limpiar_texto_y_mojibake(tipo_orig) or "").lower()
        seg = MAPA_TIPO_A_SEGMENTO.get(t_clean, "Sin clasificar")

    niv = limpiar_texto_y_mojibake(nivel_raw)
    if not niv or niv.lower() == "sin clasificar":
        c_clean = (limpiar_texto_y_mojibake(cat_orig) or "").lower()
        niv = MAPA_CAT_A_NIVEL.get(c_clean, "Sin clasificar")
    return seg, niv


def _cargar_ciclos_previos_verificables(
    cfg: ConfiguracionETL,
    anio_max: int,
    anomalias: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """Extrae únicamente ciclos históricos reales demostrables (no duplicados)."""
    ruta_hist = cfg.origen_duplicados_dir / "duplicados_afiliados_crm.csv"
    ciclos_por_emp: dict[str, list[dict[str, Any]]] = {}
    if not ruta_hist.exists():
        return ciclos_por_emp

    df_hist = pd.read_csv(ruta_hist, keep_default_na=True)
    for _, row in df_hist.iterrows():
        f_ini_p = _sanear_fecha_membresia(
            row.get("fecha_afiliacion_principal"), anio_max, anomalias
        )
        f_fin_p = _sanear_fecha_membresia(
            row.get("fecha_expiracion_principal"), anio_max, anomalias
        )
        f_ini_d = _sanear_fecha_membresia(
            row.get("fecha_afiliacion_duplicada"), anio_max, anomalias
        )
        f_fin_d = _sanear_fecha_membresia(
            row.get("fecha_expiracion_duplicada"), anio_max, anomalias
        )
        if (f_ini_d is None and f_fin_d is None) or (
            f_ini_d == f_ini_p and f_fin_d == f_fin_p
        ):
            continue
        if f_ini_p is not None and (
            (f_fin_d is not None and f_fin_d >= f_ini_p)
            or (f_ini_d is not None and f_ini_d >= f_ini_p)
        ):
            continue

        est_det = (
            limpiar_texto_y_mojibake(row.get("estado_membresia_duplicado")) or "Cancelado"
        )
        emp_id = str(row["id_empresa"]).strip()
        ciclos_por_emp.setdefault(emp_id, []).append(
            {
                "id_empresa": emp_id,
                "par_cat": _homologar_par_categoria(
                    None,
                    None,
                    tipo_orig=row.get("tipo_membresia_duplicado"),
                    cat_orig=row.get("categoria_duplicada"),
                ),
                "kam_id": None,
                "id_registro_crm_origen": limpiar_texto_y_mojibake(
                    row.get("id_registro_duplicado")
                ),
                "estado_membresia_detalle": est_det,
                "es_membresia_activa": est_det == "Activo",
                "fecha_miembro_desde": None,
                "fecha_afiliacion": f_ini_d,
                "fecha_inicio_vigencia": f_ini_d,
                "fecha_fin_vigencia": f_fin_d,
            }
        )
    return ciclos_por_emp


def _construir_ciclo_empresa_vigente(
    row: pd.Series,
    altas_fuera_crm: dict[str, dict[str, Any]],
    cfg: ConfiguracionETL,
    anio_max: int,
    anomalias: list[str],
) -> dict[str, Any]:
    """Construye el diccionario del ciclo principal de membresía de una empresa."""
    emp_id = str(row["id_empresa"]).strip()
    if bool(row.get("en_crm_afiliados", False)):
        f_afil = _sanear_fecha_membresia(row.get("fecha_afiliacion"), anio_max, anomalias)
        return {
            "id_empresa": emp_id,
            "par_cat": _homologar_par_categoria(
                row.get("segmento_membresia"),
                row.get("nivel_membresia"),
                tipo_orig=row.get("tipo_membresia_original"),
                cat_orig=row.get("categoria_membresia_original"),
            ),
            "kam_id": homologar_kam_opcional(row.get("kam_id"), cfg),
            "id_registro_crm_origen": limpiar_texto_y_mojibake(
                row.get("id_registro_crm")
            ),
            "estado_membresia_detalle": limpiar_texto_y_mojibake(
                row.get("estado_membresia_detalle")
            )
            or "Sin dato",
            "es_membresia_activa": bool(row.get("es_membresia_activa", False)),
            "fecha_miembro_desde": _sanear_fecha_membresia(
                row.get("fecha_miembro_desde"), anio_max, anomalias
            ),
            "fecha_afiliacion": f_afil,
            "fecha_inicio_vigencia": f_afil,
            "fecha_fin_vigencia": _sanear_fecha_membresia(
                row.get("fecha_expiracion"), anio_max, anomalias
            ),
        }

    mov_alta = altas_fuera_crm[emp_id]
    f_afil_m = _sanear_fecha_membresia(
        mov_alta.get("fecha_cierre_o_factura"), anio_max, anomalias
    )
    return {
        "id_empresa": emp_id,
        "par_cat": _homologar_par_categoria(None, mov_alta.get("nivel_membresia")),
        "kam_id": homologar_kam_opcional(mov_alta.get("kam_id"), cfg),
        "id_registro_crm_origen": None,
        "estado_membresia_detalle": "Activo",
        "es_membresia_activa": True,
        "fecha_miembro_desde": f_afil_m,
        "fecha_afiliacion": f_afil_m,
        "fecha_inicio_vigencia": f_afil_m,
        "fecha_fin_vigencia": _sanear_fecha_membresia(
            mov_alta.get("fecha_expiracion_afiliacion"), anio_max, anomalias
        ),
    }


def _extraer_altas_fuera_crm(df_mov_b: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Identifica empresas con alta facturada en movimientos CRM."""
    altas: dict[str, dict[str, Any]] = {}
    for _, m_row in df_mov_b.iterrows():
        t_mov = str(m_row.get("tipo_movimiento") or "")
        if bool(m_row.get("es_cierre_facturado", False)) and (
            "Nueva Afiliación" in t_mov or "Nuevo Afiliado" in t_mov
        ):
            altas[str(m_row["id_empresa"]).strip()] = {
                str(k): v for k, v in m_row.to_dict().items()
            }
    return altas


def construir_catalogo_y_membresias(
    bronze: dict[str, pd.DataFrame],
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, str], int]]:
    """Construye silver_dim_catalogo_membresia y silver_membresias."""
    anio_max = cfg.anio_analisis + 5
    anomalias: list[str] = []
    ciclos_previos = _cargar_ciclos_previos_verificables(cfg, anio_max, anomalias)
    altas_fuera_crm = _extraer_altas_fuera_crm(bronze["fact_movimientos_crm"])

    pares_catalogo: set[tuple[str, str]] = {("Sin clasificar", "Sin clasificar")}
    for _, m_row in bronze["fact_movimientos_crm"].iterrows():
        pares_catalogo.add(_homologar_par_categoria(None, m_row.get("nivel_membresia")))

    ciclos_crudos: list[dict[str, Any]] = []
    for _, row in bronze["dim_empresas"].iterrows():
        emp_id = str(row["id_empresa"]).strip()
        if not bool(row.get("en_crm_afiliados", False)) and emp_id not in altas_fuera_crm:
            continue
        for prev in ciclos_previos.get(emp_id, []):
            prev_c = dict(prev)
            prev_c["kam_id"] = homologar_kam_opcional(row.get("kam_id"), cfg)
            prev_c["fecha_miembro_desde"] = _sanear_fecha_membresia(
                row.get("fecha_miembro_desde"), anio_max, anomalias
            )
            pares_catalogo.add(prev_c["par_cat"])
            ciclos_crudos.append(prev_c)

        actual = _construir_ciclo_empresa_vigente(
            row, altas_fuera_crm, cfg, anio_max, anomalias
        )
        pares_catalogo.add(actual["par_cat"])
        ciclos_crudos.append(actual)

    mapa_cat = {par: i + 1 for i, par in enumerate(sorted(pares_catalogo))}
    dim_catalogo = pd.DataFrame(
        [
            {
                "id_cat_membresia": cid,
                "segmento_membresia": seg_n,
                "nivel_membresia": niv_n,
                "nombre_categoria": f"{seg_n} - {niv_n}",
            }
            for (seg_n, niv_n), cid in mapa_cat.items()
        ]
    )

    df_mem = pd.DataFrame(ciclos_crudos)
    df_mem["id_cat_membresia"] = df_mem["par_cat"].map(mapa_cat).astype(int)
    df_mem["_sort_ini"] = df_mem["fecha_inicio_vigencia"].fillna("0000-00-00")
    df_mem = (
        df_mem.sort_values(["id_empresa", "_sort_ini", "es_membresia_activa"])
        .drop(columns=["par_cat", "_sort_ini"])
        .reset_index(drop=True)
    )
    df_mem.insert(0, "id_membresia", [f"MEM-{i:04d}" for i in range(1, len(df_mem) + 1)])
    df_mem = df_mem[
        [
            "id_membresia",
            "id_empresa",
            "id_cat_membresia",
            "kam_id",
            "id_registro_crm_origen",
            "estado_membresia_detalle",
            "es_membresia_activa",
            "fecha_miembro_desde",
            "fecha_afiliacion",
            "fecha_inicio_vigencia",
            "fecha_fin_vigencia",
        ]
    ]
    if anomalias:
        bitacora.registrar_calidad(
            "silver_membresias",
            "fecha_afiliacion / fecha_fin_vigencia",
            tipo_inc="FECHA_FUERA_DE_RANGO_RAZONABLE",
            val_orig=", ".join(sorted(set(anomalias))),
            val_corr="Convertida a NULL sin inventar fecha sustituta",
            estado="CORREGIDO_NULO_SEGURO",
            cant=len(anomalias),
        )
    return dim_catalogo, df_mem, mapa_cat
