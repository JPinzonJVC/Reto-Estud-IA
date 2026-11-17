"""Reconstrucción y validación del historial SCD Tipo 2 para dim_empresas_scd2."""

from typing import Any

import pandas as pd

from app.modules.eda.config import ConfiguracionETL


def _cargar_registros_historicos_por_empresa(
    df_dup_orig: pd.DataFrame, cfg: ConfiguracionETL
) -> dict[str, list[dict[str, Any]]]:
    """Carga los registros históricos de afiliación agrupados por empresa.

    Args:
        df_dup_orig: DataFrame con los registros duplicados consolidados.
        cfg: Configuración del pipeline ETL Medallion.

    Returns:
        Diccionario que asocia cada id_empresa con sus registros históricos.

    """
    ruta_dup_afil = cfg.origen_duplicados_dir / "duplicados_afiliados_crm.csv"
    registros_hist: dict[str, list[dict[str, Any]]] = {}

    if ruta_dup_afil.exists():
        df_da = pd.read_csv(ruta_dup_afil, keep_default_na=True)
        for _, row in df_da.iterrows():
            emp_id = str(row["id_empresa"]).strip()
            fila_dict: dict[str, Any] = {str(k): v for k, v in row.to_dict().items()}
            registros_hist.setdefault(emp_id, []).append(fila_dict)
        return registros_hist

    df_da_sub = df_dup_orig[
        df_dup_orig["archivo_origen_csv"]
        .astype(str)
        .str.contains("Afiliados.csv", na=False)
    ]
    for _, row in df_da_sub.iterrows():
        emp_id = str(row["id_empresa"]).strip()
        registros_hist.setdefault(emp_id, []).append(
            {
                "id_empresa": emp_id,
                "id_registro_principal": "R-PRINCIPAL",
                "id_registro_duplicado": f"R-HIST-{row['id_duplicado']}",
                "estado_principal": "Inactivo",
                "estado_duplicado": "Inactivo",
                "estado_membresia_principal": "Cancelado",
                "estado_membresia_duplicado": "Cancelado",
                "tipo_membresia_principal": None,
                "tipo_membresia_duplicado": None,
                "categoria_principal": None,
                "categoria_duplicada": None,
                "fecha_afiliacion_principal": row.get("fecha_iso"),
                "fecha_afiliacion_duplicada": row.get("fecha_iso"),
                "fecha_expiracion_principal": None,
                "fecha_expiracion_duplicada": None,
            }
        )
    return registros_hist


def _crear_version_actual_empresa(
    emp_row: pd.Series, fuente_version: str
) -> dict[str, Any]:
    """Construye el diccionario de la versión vigente de una empresa en SCD2.

    Args:
        emp_row: Fila de la empresa desde dim_empresas Silver.
        fuente_version: Etiqueta que describe el origen de la versión.

    Returns:
        Diccionario con los campos de la versión actual.

    """
    return {
        "id_empresa": str(emp_row["id_empresa"]),
        "id_registro_crm": emp_row["id_registro_crm"],
        "kam_id": emp_row["kam_id"],
        "es_empresa_activa": bool(emp_row["es_empresa_activa"]),
        "es_membresia_activa": bool(emp_row["es_membresia_activa"]),
        "estado_membresia_detalle": emp_row["estado_membresia_detalle"],
        "tipo_membresia_original": emp_row["tipo_membresia_original"],
        "categoria_membresia_original": emp_row["categoria_membresia_original"],
        "fecha_inicio_vigencia": emp_row["fecha_afiliacion"],
        "fecha_fin_vigencia": emp_row["fecha_expiracion"],
        "fecha_miembro_desde_crm": emp_row["fecha_miembro_desde"],
        "es_registro_actual": True,
        "fuente_version": fuente_version,
    }


def _crear_versiones_previas_empresa(
    emp_row: pd.Series, items_dups: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reconstruye las versiones históricas previas de una empresa con duplicados CRM.

    Args:
        emp_row: Fila de la empresa desde dim_empresas Silver.
        items_dups: Lista de registros históricos asociados a la empresa.

    Returns:
        Lista de diccionarios representando las versiones históricas inactivas.

    """
    emp_id = str(emp_row["id_empresa"])
    kam_id = emp_row["kam_id"]
    primero = items_dups[0]
    id_reg_actual = (
        str(emp_row["id_registro_crm"]) if pd.notna(emp_row["id_registro_crm"]) else ""
    )
    id_reg_princ = (
        str(primero.get("id_registro_principal", ""))
        if pd.notna(primero.get("id_registro_principal"))
        else ""
    )

    versiones: list[dict[str, Any]] = []
    for idx_d, d_item in enumerate(items_dups):
        id_dup = str(d_item.get("id_registro_duplicado", ""))
        usar_princ = (
            id_dup == id_reg_actual
            and bool(id_reg_princ)
            and id_reg_princ != id_reg_actual
            and idx_d == len(items_dups) - 1
        )
        sufijo = "principal" if usar_princ else "duplicado"
        sufijo_cat = "principal" if usar_princ else "duplicada"
        id_reg = (
            id_reg_princ
            if usar_princ
            else (id_dup if id_dup else f"R-HIST-{emp_id}-{idx_d + 1}")
        )
        est_memb = d_item.get(f"estado_membresia_{sufijo}")
        versiones.append(
            {
                "id_empresa": emp_id,
                "id_registro_crm": id_reg,
                "kam_id": kam_id,
                "es_empresa_activa": (
                    str(d_item.get(f"estado_{sufijo}", "")).strip() == "Activo"
                ),
                "es_membresia_activa": str(est_memb or "").strip() == "Activo",
                "estado_membresia_detalle": (
                    est_memb if pd.notna(est_memb) else "Sin dato"
                ),
                "tipo_membresia_original": d_item.get(f"tipo_membresia_{sufijo}"),
                "categoria_membresia_original": d_item.get(f"categoria_{sufijo_cat}"),
                "fecha_inicio_vigencia": d_item.get(f"fecha_afiliacion_{sufijo_cat}"),
                "fecha_fin_vigencia": d_item.get(f"fecha_expiracion_{sufijo_cat}"),
                "fecha_miembro_desde_crm": emp_row["fecha_miembro_desde"],
                "es_registro_actual": False,
                "fuente_version": "HISTORIAL_SCD2_AFILIADOS_CRM",
            }
        )
    return versiones


def _detectar_empresas_con_intervalos_superpuestos(
    df_scd2: pd.DataFrame,
) -> set[str]:
    """Identifica las empresas cuyas versiones presentan intervalos superpuestos.

    Args:
        df_scd2: DataFrame con todas las versiones SCD2 ordenadas.

    Returns:
        Conjunto de identificadores de empresa con solapamiento temporal.

    """
    superpuestos_emp: set[str] = set()
    df_mult = df_scd2[df_scd2["total_versiones_empresa"] > 1]
    for emp_id, grp in df_mult.groupby("id_empresa"):
        inis = pd.to_datetime(grp["fecha_inicio_vigencia"], errors="coerce").tolist()
        fins = pd.to_datetime(grp["fecha_fin_vigencia"], errors="coerce").tolist()
        inis_validos = [x for x in inis if pd.notna(x)]
        if len(inis_validos) != len(set(inis_validos)):
            superpuestos_emp.add(str(emp_id))
            continue
        if _hay_solapamiento_entre_pares(inis, fins):
            superpuestos_emp.add(str(emp_id))
    return superpuestos_emp


def _hay_solapamiento_entre_pares(inis: list[Any], fins: list[Any]) -> bool:
    """Evalúa si dos intervalos en una lista de inicios y fines se superponen.

    Args:
        inis: Lista de fechas de inicio convertidas a Timestamp/NaT.
        fins: Lista de fechas de fin convertidas a Timestamp/NaT.

    Returns:
        True si existe al menos un par de intervalos superpuestos.

    """
    total = len(inis)
    for i in range(total - 1):
        for j in range(i + 1, total):
            s1, e1, s2, e2 = inis[i], fins[i], inis[j], fins[j]
            if pd.notna(s1) and pd.notna(e1) and pd.notna(s2) and pd.notna(e2):
                if max(s1, s2) <= min(e1, e2):
                    return True
            elif pd.notna(e1) and pd.notna(s2) and e1 >= s2:
                return True
    return False


def _clasificar_reconstruccion_scd2(row: pd.Series) -> str:
    """Clasifica el estado de reconstrucción histórica de una fila en SCD2.

    Args:
        row: Serie correspondiente a una versión en dim_empresas_scd2.

    Returns:
        Categoría de clasificación de la historia SCD2.

    """
    if row["fuente_version"] == "PROSPECTO_SIN_HISTORIAL_CRM":
        return "NO_APLICA_PROSPECTO_SIN_CRM"
    if row["tiene_fechas_inconsistentes"]:
        return "FECHA_INCONSISTENTE_INICIO_MAYOR_FIN"
    if row["tiene_intervalo_superpuesto"]:
        return "INTERVALO_SUPERPUESTO_O_AMBIGUO_EN_ORIGEN"
    tiene_ini = (
        pd.notna(row["fecha_inicio_vigencia"])
        and str(row["fecha_inicio_vigencia"]).strip() != ""
    )
    tiene_fin = (
        pd.notna(row["fecha_fin_vigencia"])
        and str(row["fecha_fin_vigencia"]).strip() != ""
    )
    mapa_vigencia = {
        (True, True): "VIGENCIA_COMPLETA_RECONSTRUIDA",
        (True, False): "VIGENCIA_PARCIAL_SIN_FECHA_FIN",
        (False, True): "HISTORIA_PARCIAL_SIN_FECHA_INICIO",
        (False, False): "HISTORIA_NO_RECONSTRUIBLE_SIN_FECHAS_EN_ORIGEN",
    }
    return mapa_vigencia[(tiene_ini, tiene_fin)]


def _describir_version_scd2(row: pd.Series) -> str:
    """Genera una descripción legible para la versión SCD2 de una empresa.

    Args:
        row: Serie correspondiente a una versión en dim_empresas_scd2.

    Returns:
        Descripción textual del registro en SCD2.

    """
    if row["fuente_version"] == "PROSPECTO_SIN_HISTORIAL_CRM":
        return (
            "Versión única actual de empresa asistente o encuestada "
            "no registrada en CRM"
        )
    if row["total_versiones_empresa"] == 1:
        return "Versión única actual de empresa afiliada/registrada en Zoho CRM"
    ver = f"({row['version_registro']}/{row['total_versiones_empresa']})"
    if row["es_registro_actual"]:
        return f"Versión actual consolidada {ver} tras múltiples registros en CRM"
    return f"Versión histórica previa/inactiva {ver} en Zoho CRM"


def construir_dim_empresas_scd2(
    df_emp_silver: pd.DataFrame,
    df_dup_orig: pd.DataFrame,
    cfg: ConfiguracionETL,
) -> pd.DataFrame:
    """Construye dim_empresas_scd2 validando fechas, versiones y solapamientos.

    Args:
        df_emp_silver: DataFrame depurado de dim_empresas en capa Silver.
        df_dup_orig: DataFrame de registros duplicados desde capa Bronze.
        cfg: Configuración del pipeline ETL Medallion.

    Returns:
        DataFrame de dim_empresas_scd2 listo para persistir en Silver.

    """
    registros_hist_por_emp = _cargar_registros_historicos_por_empresa(df_dup_orig, cfg)
    versiones_lista: list[dict[str, Any]] = []

    for _, emp_row in df_emp_silver.iterrows():
        emp_id = str(emp_row["id_empresa"])
        en_crm = bool(emp_row["en_crm_afiliados"])
        if emp_id not in registros_hist_por_emp:
            fuente = "REGISTRO_UNICO_CRM" if en_crm else "PROSPECTO_SIN_HISTORIAL_CRM"
            versiones_lista.append(_crear_version_actual_empresa(emp_row, fuente))
        else:
            versiones_lista.extend(
                _crear_versiones_previas_empresa(emp_row, registros_hist_por_emp[emp_id])
            )
            versiones_lista.append(
                _crear_version_actual_empresa(emp_row, "VERSION_ACTUAL_CONSOLIDADA_CRM")
            )

    df_scd2 = pd.DataFrame(versiones_lista)
    df_scd2["_sort_ini"] = (
        df_scd2["fecha_inicio_vigencia"].fillna("0000-00-00").astype(str)
    )
    df_scd2["_sort_fin"] = df_scd2["fecha_fin_vigencia"].fillna("0000-00-00").astype(str)
    df_scd2 = (
        df_scd2.sort_values(
            [
                "id_empresa",
                "es_registro_actual",
                "_sort_ini",
                "_sort_fin",
                "id_registro_crm",
            ],
            ascending=[True, True, True, True, True],
        )
        .drop(columns=["_sort_ini", "_sort_fin"])
        .reset_index(drop=True)
    )

    df_scd2["version_registro"] = df_scd2.groupby("id_empresa").cumcount() + 1
    df_scd2["total_versiones_empresa"] = df_scd2.groupby("id_empresa")[
        "version_registro"
    ].transform("max")

    ini_dt = pd.to_datetime(df_scd2["fecha_inicio_vigencia"], errors="coerce")
    fin_dt = pd.to_datetime(df_scd2["fecha_fin_vigencia"], errors="coerce")
    df_scd2["tiene_fechas_inconsistentes"] = (
        ini_dt.notna() & fin_dt.notna() & (ini_dt > fin_dt)
    )

    superpuestos_emp = _detectar_empresas_con_intervalos_superpuestos(df_scd2)
    df_scd2["tiene_intervalo_superpuesto"] = df_scd2["id_empresa"].isin(superpuestos_emp)
    df_scd2["clasificacion_historia_scd2"] = df_scd2.apply(
        _clasificar_reconstruccion_scd2, axis=1
    )
    df_scd2["descripcion_version_scd2"] = df_scd2.apply(_describir_version_scd2, axis=1)
    df_scd2.insert(
        0,
        "sk_empresa_scd2",
        [f"SCD2-EMP-{i:04d}" for i in range(1, len(df_scd2) + 1)],
    )
    return df_scd2
