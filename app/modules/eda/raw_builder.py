"""Constructor de tablas normalizadas desde los 47 CSV crudos originales de ACTHO."""

# pylint: disable=too-many-lines,too-many-locals,too-many-branches,too-many-statements

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from app.modules.eda.config import ConfiguracionETL, cargar_configuracion
from app.modules.eda.normalizer import (
    limpiar_texto_y_mojibake,
    normalizar_booleano,
    normalizar_fecha_iso,
)

logger = logging.getLogger(__name__)

EXTRA_MOJIBAKE: tuple[tuple[str, str], ...] = (
    ("Estﾃ｡ndar", "Estándar"),
    ("Jﾃｳvenes", "Jóvenes"),
    ("Bogotﾃ｡", "Bogotá"),
    ("Medellﾃｭn", "Medellín"),
    ("ﾃ｡", "á"),
    ("ﾃｩ", "é"),
    ("ﾃｭ", "í"),
    ("ﾃｳ", "ó"),
    ("ﾃｺ", "ú"),
    ("ﾃｱ", "ñ"),
)

MESES_ES_NUM: dict[str, int] = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


def _clean_text(valor: Any) -> str | None:
    """Limpia texto, espacios y variantes adicionales de mojibake."""
    texto = limpiar_texto_y_mojibake(valor)
    if texto is None:
        return None
    for mal, bien in EXTRA_MOJIBAKE:
        texto = texto.replace(mal, bien)
    texto = re.sub(r"\s+", " ", texto).strip()
    if not texto or texto.lower() in ("nan", "none", "null", "sin dato", "-"):
        return None
    return texto


def _clean_id(valor: Any) -> str | None:
    """Normaliza identificadores de negocio (EMP-xxxx, P-xxxx, R-xxxx)."""
    texto = _clean_text(valor)
    if texto is None:
        return None
    return texto.strip()


def _clean_kam_label(valor: Any) -> str:
    """Limpia etiquetas de KAM eliminando conteos agrupados de Zoho."""
    texto = _clean_text(valor)
    if not texto:
        return "Sin asignar"
    texto = re.sub(r"\s*\(\s*\d+\s*\)\s*$", "", texto).strip()
    texto = re.sub(r"^BD\s+", "", texto, flags=re.IGNORECASE).strip()
    return texto or "Sin asignar"


def _parse_fecha_es(valor: Any) -> str | None:
    """Convierte fechas en español (incluyendo 'sept 30, 2027') a YYYY-MM-DD."""
    texto = _clean_text(valor)
    if texto is None:
        return None
    texto = re.sub(r"\s*\(\s*\d+\s*\)\s*$", "", texto).strip()
    texto = re.sub(r"\bsept\.?\b", "sep", texto, flags=re.IGNORECASE)
    return normalizar_fecha_iso(texto)


def _parse_datetime_es(valor: Any) -> pd.Timestamp | None:
    """Parsea timestamps en español de encuestas a Timestamp."""
    texto = _clean_text(valor)
    if texto is None:
        return None
    norm = texto.replace("a. m.", "AM").replace("p. m.", "PM")
    norm = norm.replace("a.\xa0m.", "AM").replace("p.\xa0m.", "PM")
    reemplazos = {
        "ene": "Jan",
        "feb": "Feb",
        "mar": "Mar",
        "abr": "Apr",
        "may": "May",
        "jun": "Jun",
        "jul": "Jul",
        "ago": "Aug",
        "sept": "Sep",
        "sep": "Sep",
        "oct": "Oct",
        "nov": "Nov",
        "dic": "Dec",
    }
    for es, en in reemplazos.items():
        norm = re.sub(rf"\b{es}\.?", en, norm, flags=re.IGNORECASE)
    ts = pd.to_datetime(norm, errors="coerce")
    if pd.isna(ts):
        return None
    return ts


def _parse_float(valor: Any) -> float | None:
    """Convierte porcentajes o números en texto a float."""
    texto = _clean_text(valor)
    if texto is None:
        return None
    limpio = texto.replace("%", "").replace(",", ".").strip()
    try:
        return float(limpio)
    except ValueError:
        return None


def _parse_int(valor: Any) -> int | None:
    """Convierte valores numéricos a int o None."""
    num = _parse_float(valor)
    if num is None or np.isnan(num):
        return None
    return int(round(num))


def _flag_bool(valor: Any) -> bool:
    """Convierte valores heterogéneos de CRM/encuestas a bool estricto."""
    res = normalizar_booleano(valor)
    return bool(res) if res is not None else False


def _normalizar_nivel_membresia(tipo: str | None, cat: str | None) -> str | None:
    """Homologa nivel de membresía (Elite, Premium, Estándar, Personal)."""
    combinado = f"{cat or ''} {tipo or ''}".lower()
    if "elite" in combinado:
        return "Elite"
    if "premium" in combinado:
        return "Premium"
    if "estándar" in combinado or "estandar" in combinado:
        return "Estándar"
    if "plus" in combinado:
        return "Plus"
    if "personal" in combinado or "persona natural" in combinado:
        return "Personal"
    return cat or tipo


def _normalizar_segmento_membresia(tipo: str | None, cat: str | None) -> str | None:
    """Clasifica el segmento comercial de la membresía."""
    combinado = f"{tipo or ''} {cat or ''}".lower()
    if "consultor" in combinado or "vendor" in combinado:
        return "Consultora / Vendor"
    if "universidad" in combinado:
        return "Universidad"
    if (
        "persona natural" in combinado
        or "personal" in combinado
        or "jovenes" in combinado
        or "jóvenes" in combinado
    ):
        return "Personal / Independiente"
    if (
        "empresa" in combinado
        or "corporativ" in combinado
        or "estándar" in combinado
        or "premium" in combinado
        or "elite" in combinado
    ):
        return "Corporativa / Empresa"
    return tipo


def _leer_matriz_general(
    raw_dir: Path,
) -> tuple[dict[tuple[str, int], int], dict[int, int], dict[str, int]]:
    """Lee GENERAL (2).csv y retorna conteos (empresa, evento), evento y empresa."""
    ruta = raw_dir / "Asistencia eventos" / "GENERAL (2).csv"
    por_emp_ev: dict[tuple[str, int], int] = {}
    por_ev: dict[int, int] = {}
    por_emp: dict[str, int] = {}
    if not ruta.exists():
        return por_emp_ev, por_ev, por_emp

    df_raw = pd.read_csv(ruta, header=None, dtype=str)
    header_idx = 2
    for idx in range(min(6, len(df_raw))):
        fila = " ".join(str(v) for v in df_raw.iloc[idx].dropna()).lower()
        if "id_empresa" in fila:
            header_idx = idx
            break

    encabezados = df_raw.iloc[header_idx].tolist()
    ev_cols: dict[int, int] = {}
    for col_idx, val in enumerate(encabezados):
        v_txt = _clean_text(val)
        if v_txt and v_txt.isdigit():
            ev_num = int(v_txt)
            if 1 <= ev_num <= 60:
                ev_cols[col_idx] = ev_num

    start_row = header_idx + 1
    for _, row in df_raw.iloc[start_row:].iterrows():
        emp_id = _clean_id(row.iloc[0])
        if not emp_id or not emp_id.startswith("EMP-"):
            continue
        emp_total = 0
        for col_idx, ev_num in ev_cols.items():
            if col_idx >= len(row):
                continue
            cnt = _parse_int(row.iloc[col_idx])
            if cnt and cnt > 0:
                por_emp_ev[(emp_id, ev_num)] = cnt
                por_ev[ev_num] = por_ev.get(ev_num, 0) + cnt
                emp_total += cnt
        if emp_total > 0:
            por_emp[emp_id] = por_emp.get(emp_id, 0) + emp_total
    return por_emp_ev, por_ev, por_emp


def _construir_eventos_y_asistencias(
    raw_dir: Path,
    kam_por_empresa: dict[str, str],
    matriz_emp_ev: dict[tuple[str, int], int],
    matriz_por_ev: dict[int, int],
    duplicados_rows: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construye dim_eventos y fact_asistencias desde HOMOLOGACION y los 34 CSV."""
    ev_dir = raw_dir / "Asistencia eventos"
    hom_path = ev_dir / "HOMOLOGACION OFERTA 2027.csv"
    df_hom = pd.read_csv(hom_path, skiprows=2, dtype=str)
    df_hom = df_hom[df_hom["Hoja de origen"].notna()].copy()

    eventos_rows: list[dict[str, Any]] = []
    asist_rows: list[dict[str, Any]] = []
    seq_asist = 1

    for _, row in df_hom.iterrows():
        id_ev = _parse_int(row.iloc[0])
        hoja = _clean_text(row.iloc[1])
        if id_ev is None or not hoja:
            continue
        fecha_ev = _parse_fecha_es(row.iloc[2])
        periodo = fecha_ev[:7] if fecha_ev else None
        nombre_ev = _clean_text(row.iloc[3])
        linea = _clean_text(row.iloc[4])
        detalle = _clean_text(row.iloc[5])
        modalidad = _clean_text(row.iloc[6])
        es_presencial = bool(
            modalidad and modalidad.lower() in ("presencial", "híbrido", "hibrido")
        )

        archivo_csv = f"{hoja}.csv"
        fpath = ev_dir / archivo_csv
        vistas_evento: dict[tuple[str | None, str], int] = {}
        ev_asist_count = 0
        ev_emps: set[str] = set()
        ev_pers: set[str] = set()

        if fpath.exists() and fpath.stat().st_size > 10:
            df_raw = pd.read_csv(fpath, header=None, dtype=str)
            h_idx = 0
            for pos in range(min(5, len(df_raw))):
                txt = " ".join(str(v) for v in df_raw.iloc[pos].dropna()).lower()
                if "id_empresa" in txt or "id_persona" in txt:
                    h_idx = pos
                    break

            headers = [
                str(v).strip() if pd.notna(v) else "" for v in df_raw.iloc[h_idx].tolist()
            ]
            col_map: dict[str, int] = {}
            for idx_c, h in enumerate(headers):
                hl = h.lower()
                if "id_empresa" in hl:
                    col_map["id_empresa"] = idx_c
                elif "id_persona" in hl:
                    col_map["id_persona"] = idx_c
                elif "nivel de cargo" in hl:
                    col_map["nivel_cargo"] = idx_c
                elif hl == "ciudad" or hl.startswith("ciudad"):
                    col_map["ciudad"] = idx_c
                elif "costo" in hl:
                    col_map["costo"] = idx_c
                elif "autoriz" in hl or "proteccion de datos" in hl:
                    col_map["autoriza"] = idx_c
                elif "ubicaci" in hl:
                    col_map["ubicacion"] = idx_c
                elif "inscrito" in hl:
                    col_map["inscritos"] = idx_c
                elif idx_c == 0:
                    col_map["afiliado"] = 0

            if "afiliado" not in col_map:
                col_map["afiliado"] = 0
            if "inscritos" not in col_map and len(headers) > 7 and headers[7] == "":
                col_map["inscritos"] = 7

            start_ev_row = h_idx + 1
            for raw_pos, r in df_raw.iloc[start_ev_row:].iterrows():
                id_per = (
                    _clean_id(r.iloc[col_map["id_persona"]])
                    if "id_persona" in col_map
                    else None
                )
                id_emp = (
                    _clean_id(r.iloc[col_map["id_empresa"]])
                    if "id_empresa" in col_map
                    else None
                )
                if not id_per and not id_emp:
                    continue
                if not id_per:
                    continue

                llave = (id_emp, id_per)
                fila_csv = int(str(raw_pos)) + 1
                if llave in vistas_evento:
                    duplicados_rows.append(
                        {
                            "id_duplicado": f"DUP-{len(duplicados_rows) + 1:04d}",
                            "tabla_normalizada_afectada": "fact_asistencias.csv",
                            "archivo_origen_csv": f"Asistencia eventos/{archivo_csv}",
                            "fila_origen_csv": fila_csv,
                            "tipo_duplicado": "Duplicado exacto en el evento",
                            "llave_negocio": f"id_evento={id_ev}|id_persona={id_per}",
                            "id_empresa": id_emp,
                            "id_persona": id_per,
                            "id_evento": id_ev,
                            "fecha_iso": fecha_ev,
                            "regla_identificacion": (
                                "Misma persona y empresa en el mismo evento"
                            ),
                            "detalle_primera_aparicion": f"Fila {vistas_evento[llave]}",
                            "detalle_duplicado": f"Fila {fila_csv}",
                        }
                    )
                    continue
                vistas_evento[llave] = fila_csv

                raw_afil = r.iloc[col_map["afiliado"]] if "afiliado" in col_map else None
                raw_afil_txt = (_clean_text(raw_afil) or "").lower()
                if raw_afil_txt in ("1", "si", "sí", "afiliado", "true"):
                    es_afil = True
                elif raw_afil_txt in ("0", "no", "no afiliado", "invitado", "false"):
                    es_afil = False
                else:
                    es_afil = bool(id_emp and id_emp in kam_por_empresa)

                nivel_cargo = (
                    _clean_text(r.iloc[col_map["nivel_cargo"]])
                    if "nivel_cargo" in col_map
                    else None
                )
                ciudad_ev = (
                    _clean_text(r.iloc[col_map["ciudad"]])
                    if "ciudad" in col_map
                    else None
                )
                cant_ins = (
                    _parse_int(r.iloc[col_map["inscritos"]])
                    if "inscritos" in col_map
                    else 1
                )
                if not cant_ins or cant_ins <= 0:
                    cant_ins = 1
                tiene_costo = (
                    normalizar_booleano(r.iloc[col_map["costo"]])
                    if "costo" in col_map
                    else None
                )
                autoriza = (
                    normalizar_booleano(r.iloc[col_map["autoriza"]])
                    if "autoriza" in col_map
                    else None
                )
                confirmado = (
                    normalizar_booleano(r.iloc[col_map["ubicacion"]])
                    if "ubicacion" in col_map
                    else None
                )

                conteo_mat = matriz_emp_ev.get((id_emp, id_ev), 0) if id_emp else 0
                asist_rows.append(
                    {
                        "id_asistencia": f"A-{seq_asist:05d}",
                        "id_evento": id_ev,
                        "id_empresa": id_emp,
                        "id_persona": id_per,
                        "kam_id": (
                            kam_por_empresa.get(id_emp, "Sin asignar")
                            if id_emp
                            else "Sin asignar"
                        ),
                        "fecha_evento": fecha_ev,
                        "periodo_mes_iso": periodo,
                        "nivel_cargo": nivel_cargo,
                        "ciudad_evento": ciudad_ev,
                        "cantidad_inscritos": cant_ins,
                        "es_afiliado": es_afil,
                        "tiene_costo": tiene_costo,
                        "autoriza_tratamiento_datos": autoriza,
                        "confirmado_ubicacion_principal": confirmado,
                        "reflejado_en_matriz_general": conteo_mat > 0,
                        "conteo_empresa_matriz_general": conteo_mat,
                    }
                )
                seq_asist += 1
                ev_asist_count += 1
                if id_emp:
                    ev_emps.add(id_emp)
                ev_pers.add(id_per)

        eventos_rows.append(
            {
                "id_evento": id_ev,
                "archivo_csv": archivo_csv,
                "fecha_evento": fecha_ev,
                "fecha_inicio_evento": fecha_ev,
                "fecha_fin_evento": fecha_ev,
                "periodo_mes_iso": periodo,
                "nombre_evento": nombre_ev,
                "linea_oferta_2027": linea,
                "experiencia_detalle": detalle,
                "modalidad": modalidad,
                "es_presencial": es_presencial,
                "tiene_asistentes_registrados": ev_asist_count > 0,
                "total_asistentes_archivo": ev_asist_count,
                "empresas_unicas_archivo": len(ev_emps),
                "personas_unicas_archivo": len(ev_pers),
                "total_reportado_matriz_general": matriz_por_ev.get(id_ev, 0),
            }
        )

    return pd.DataFrame(eventos_rows), pd.DataFrame(asist_rows)


def _construir_encuestas(raw_dir: Path) -> pd.DataFrame:
    """Consolida encuestas presenciales y virtuales en fact_encuestas_satisfaccion."""
    fuentes = (
        (raw_dir / "EVENTO~1.XLS - Responses.csv", "Presencial", True),
        (raw_dir / "eventos_dos.csv", "Virtual", False),
    )
    filas: list[dict[str, Any]] = []
    vistos: set[str] = set()

    for ruta, modalidad, es_pres in fuentes:
        if not ruta.exists():
            continue
        df_raw = pd.read_csv(ruta, skiprows=1, dtype=str)
        for _, r in df_raw.iterrows():
            id_resp = _clean_id(r.iloc[1]) if len(r) > 1 else None
            if not id_resp or id_resp in vistos:
                continue
            vistos.add(id_resp)

            ts_ini = _parse_datetime_es(r.iloc[2]) if len(r) > 2 else None
            ts_fin = _parse_datetime_es(r.iloc[3]) if len(r) > 3 else None
            fecha_enc = ts_ini.strftime("%Y-%m-%d") if ts_ini is not None else None
            periodo = fecha_enc[:7] if fecha_enc else None
            duracion = (
                int((ts_fin - ts_ini).total_seconds())
                if ts_ini is not None and ts_fin is not None and ts_fin >= ts_ini
                else None
            )

            c_loc = _parse_int(r.iloc[6]) if len(r) > 6 else None
            c_conv = _parse_int(r.iloc[7]) if len(r) > 7 else None
            c_conf = _parse_int(r.iloc[8]) if len(r) > 8 else None
            c_rel = _parse_int(r.iloc[9]) if len(r) > 9 else None
            notas = [c for c in (c_loc, c_conv, c_conf, c_rel) if c is not None]
            prom = round(sum(notas) / len(notas), 2) if notas else None

            temarios = _clean_text(r.iloc[10]) if len(r) > 10 else None
            desea_act = normalizar_booleano(r.iloc[11]) if len(r) > 11 else None
            id_per = _clean_id(r.iloc[12]) if len(r) > 12 else None
            id_emp = _clean_id(r.iloc[13]) if len(r) > 13 else None
            ciudad = _clean_text(r.iloc[14]) if len(r) > 14 else None
            en_crm = normalizar_booleano(r.iloc[17]) if len(r) > 17 else None
            metodo = _clean_text(r.iloc[18]) if len(r) > 18 else None

            filas.append(
                {
                    "id_respuesta": id_resp,
                    "modalidad_encuesta": modalidad,
                    "es_modalidad_presencial": es_pres,
                    "fecha_encuesta": fecha_enc,
                    "periodo_mes_iso": periodo,
                    "fecha_hora_inicio": (
                        ts_ini.strftime("%Y-%m-%d %H:%M:%S")
                        if ts_ini is not None
                        else None
                    ),
                    "fecha_hora_fin": (
                        ts_fin.strftime("%Y-%m-%d %H:%M:%S")
                        if ts_fin is not None
                        else None
                    ),
                    "duracion_segundos": duracion,
                    "calif_locacion_o_plataforma": c_loc,
                    "calif_convocatoria_publicidad": c_conv,
                    "calif_conferencistas": c_conf,
                    "calif_relevancia_temas": c_rel,
                    "promedio_satisfaccion": prom,
                    "temarios_sugeridos": temarios,
                    "desea_recibir_actualizaciones": desea_act,
                    "id_persona": id_per,
                    "id_empresa": id_emp,
                    "ciudad": ciudad,
                    "empresa_en_crm": en_crm,
                    "metodo_asignacion_empresa": metodo,
                }
            )
    return pd.DataFrame(filas)


def _parse_mes_anio(texto: str | None) -> tuple[str | None, str | None]:
    """Convierte 'Agosto 2026 ( 6 )' o 'Agosto' a (YYYY-MM-01, YYYY-MM)."""
    if not texto:
        return None, None
    limpio = re.sub(r"\s*\(\s*\d+\s*\)\s*$", "", texto).strip().lower()
    partes = limpio.split()
    mes = MESES_ES_NUM.get(partes[0]) if partes else None
    if mes is None:
        return None, None
    anio = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 2026
    return f"{anio:04d}-{mes:02d}-01", f"{anio:04d}-{mes:02d}"


def _construir_movimientos_crm(
    raw_dir: Path,
    kam_por_empresa: dict[str, str],
    nivel_por_empresa: dict[str, str | None],
) -> tuple[pd.DataFrame, dict[str, str], dict[str, str | None]]:
    """Consolida afiliaciones, renovaciones, tratos en estado y nuevos afiliados."""
    movs: list[dict[str, Any]] = []
    fecha_export = "2026-11-13"

    # 1. afiliaciones.csv (Nuevas afiliaciones últimos 2 meses)
    afil_path = raw_dir / "afiliaciones.csv"
    if afil_path.exists():
        df_a = pd.read_csv(afil_path, skiprows=6, dtype=str)
        cur_mes: str | None = None
        cur_kam: str = "Sin asignar"
        cur_fecha: str | None = None
        for _, r in df_a.iterrows():
            c0 = _clean_text(r.iloc[0]) if len(r) > 0 else None
            if c0 and "grand total" in c0.lower():
                break
            if c0:
                cur_mes = c0
            c1 = _clean_text(r.iloc[1]) if len(r) > 1 else None
            if c1:
                cur_kam = _clean_kam_label(c1)
            c2 = _clean_text(r.iloc[2]) if len(r) > 2 else None
            if c2:
                cur_fecha = _parse_fecha_es(c2)
            emp_id = _clean_id(r.iloc[3]) if len(r) > 3 else None
            if not emp_id or not emp_id.startswith("EMP-"):
                continue
            cat = _clean_text(r.iloc[4]) if len(r) > 4 else None
            f_mes, p_mes = _parse_mes_anio(cur_mes)
            movs.append(
                {
                    "tipo_movimiento": "Nueva Afiliación (Últ. 2 Meses)",
                    "es_cierre_facturado": True,
                    "es_renovacion": False,
                    "fecha_periodo_mes": f_mes,
                    "periodo_mes_iso": p_mes or (cur_fecha[:7] if cur_fecha else None),
                    "fecha_cierre_o_factura": cur_fecha,
                    "fecha_expiracion_afiliacion": None,
                    "fecha_exportacion_reporte": fecha_export,
                    "kam_id": cur_kam,
                    "id_empresa": emp_id,
                    "nivel_membresia": _normalizar_nivel_membresia(None, cat),
                    "id_persona_contacto": None,
                }
            )

    # 2. informe_renovaviones_ult_2_meses.csv
    ren_path = raw_dir / "informe_renovaviones_ult_2_meses.csv"
    if ren_path.exists():
        df_r = pd.read_csv(ren_path, skiprows=6, dtype=str)
        cur_mes = None
        cur_kam = "Sin asignar"
        for _, r in df_r.iterrows():
            c0 = _clean_text(r.iloc[0]) if len(r) > 0 else None
            if c0 and "grand total" in c0.lower():
                break
            if c0:
                cur_mes = c0
            c1 = _clean_text(r.iloc[1]) if len(r) > 1 else None
            if c1:
                cur_kam = _clean_kam_label(c1)
            emp_id = _clean_id(r.iloc[2]) if len(r) > 2 else None
            if not emp_id or not emp_id.startswith("EMP-"):
                continue
            f_exp = _parse_fecha_es(r.iloc[3]) if len(r) > 3 else None
            f_mes, p_mes = _parse_mes_anio(cur_mes)
            movs.append(
                {
                    "tipo_movimiento": "Renovación (Últ. 2 Meses)",
                    "es_cierre_facturado": True,
                    "es_renovacion": True,
                    "fecha_periodo_mes": f_mes,
                    "periodo_mes_iso": p_mes,
                    "fecha_cierre_o_factura": f_mes,
                    "fecha_expiracion_afiliacion": f_exp,
                    "fecha_exportacion_reporte": fecha_export,
                    "kam_id": cur_kam,
                    "id_empresa": emp_id,
                    "nivel_membresia": nivel_por_empresa.get(emp_id),
                    "id_persona_contacto": None,
                }
            )

    # 3. estado.csv (Tratos en Estado)
    est_path = raw_dir / "estado.csv"
    if est_path.exists():
        df_e = pd.read_csv(est_path, dtype=str)
        for _, r in df_e.iterrows():
            emp_id = _clean_id(r.iloc[1]) if len(r) > 1 else None
            if not emp_id or not emp_id.startswith("EMP-"):
                continue
            kam = _clean_kam_label(r.iloc[0])
            movs.append(
                {
                    "tipo_movimiento": "Trato en Estado",
                    "es_cierre_facturado": False,
                    "es_renovacion": False,
                    "fecha_periodo_mes": None,
                    "periodo_mes_iso": None,
                    "fecha_cierre_o_factura": None,
                    "fecha_expiracion_afiliacion": None,
                    "fecha_exportacion_reporte": fecha_export,
                    "kam_id": kam,
                    "id_empresa": emp_id,
                    "nivel_membresia": nivel_por_empresa.get(emp_id),
                    "id_persona_contacto": None,
                }
            )

    # 4. nuevos_afiliados.csv
    nuevos_persona_emp: dict[str, str] = {}
    nuevos_persona_fecha: dict[str, str | None] = {}
    nuev_path = raw_dir / "nuevos_afiliados.csv"
    if nuev_path.exists():
        df_n = pd.read_csv(nuev_path, dtype=str)
        for _, r in df_n.iterrows():
            mes_txt = _clean_text(r.iloc[0]) if len(r) > 0 else None
            emp_id = _clean_id(r.iloc[1]) if len(r) > 1 else None
            per_id = _clean_id(r.iloc[2]) if len(r) > 2 else None
            if not emp_id or not emp_id.startswith("EMP-"):
                continue
            f_mes, p_mes = _parse_mes_anio(mes_txt)
            if per_id:
                nuevos_persona_emp[per_id] = emp_id
                nuevos_persona_fecha[per_id] = f_mes
            movs.append(
                {
                    "tipo_movimiento": "Nuevo Afiliado (Directorio)",
                    "es_cierre_facturado": True,
                    "es_renovacion": False,
                    "fecha_periodo_mes": f_mes,
                    "periodo_mes_iso": p_mes,
                    "fecha_cierre_o_factura": f_mes,
                    "fecha_expiracion_afiliacion": None,
                    "fecha_exportacion_reporte": fecha_export,
                    "kam_id": kam_por_empresa.get(emp_id, "Sin asignar"),
                    "id_empresa": emp_id,
                    "nivel_membresia": nivel_por_empresa.get(emp_id),
                    "id_persona_contacto": per_id,
                }
            )

    return pd.DataFrame(movs), nuevos_persona_emp, nuevos_persona_fecha


def construir_normalizados_desde_raw(
    cfg: ConfiguracionETL | None = None,
) -> dict[str, pd.DataFrame]:
    """Genera las 8 tablas normalizadas y duplicados a partir de input/CSV.

    Args:
        cfg: Configuración del pipeline ETL Medallion.

    Returns:
        Diccionario con los DataFrames normalizados generados.

    """
    cfg = cfg or cargar_configuracion()
    raw_dir = cfg.origen_raw_csv_dir
    if raw_dir is None or not raw_dir.exists():
        raise FileNotFoundError(f"Directorio de CSV crudos no encontrado: {raw_dir}")

    cfg.origen_normalizados_dir.mkdir(parents=True, exist_ok=True)
    cfg.origen_duplicados_dir.mkdir(parents=True, exist_ok=True)

    duplicados_rows: list[dict[str, Any]] = []
    dup_crm_rows: list[dict[str, Any]] = []

    # 1. Leer Afiliados.csv y separar duplicados históricos (SCD2)
    df_af_raw = pd.read_csv(raw_dir / "Afiliados.csv", dtype=str)
    df_af_raw["_fila_csv"] = range(2, len(df_af_raw) + 2)
    df_af_raw["_id_empresa"] = df_af_raw["Nombre de Empresa [anonimizado]"].apply(
        _clean_id
    )
    df_af_raw = df_af_raw[df_af_raw["_id_empresa"].notna()].copy()

    # Ordenar para priorizar registros Activos / más recientes como registro principal
    df_af_raw["_score_activo"] = (
        (df_af_raw["Estado de la Membresía"].fillna("").str.strip() == "Activo").astype(
            int
        )
        * 4
        + (df_af_raw["Estado"].fillna("").str.strip() == "Activo").astype(int) * 2
        + df_af_raw["Fecha de Expiración Afiliación"].notna().astype(int)
    )
    df_af_raw["_fecha_exp_sort"] = df_af_raw["Fecha de Expiración Afiliación"].fillna("")
    df_af_sorted = df_af_raw.sort_values(
        by=["_id_empresa", "_score_activo", "_fecha_exp_sort", "_fila_csv"],
        ascending=[True, False, False, True],
    )

    principales_list: list[pd.Series] = []
    for emp_key, grp in df_af_sorted.groupby("_id_empresa", sort=False):
        emp_id = str(emp_key)
        princ = grp.iloc[0]
        principales_list.append(princ)
        for _, dup in grp.iloc[1:].iterrows():
            dup_id = f"DUP-{len(duplicados_rows) + 1:04d}"
            f_afil_p = _parse_fecha_es(princ.get("Fecha de Afiliación"))
            f_afil_d = _parse_fecha_es(dup.get("Fecha de Afiliación"))
            f_exp_p = _parse_fecha_es(princ.get("Fecha de Expiración Afiliación"))
            f_exp_d = _parse_fecha_es(dup.get("Fecha de Expiración Afiliación"))
            duplicados_rows.append(
                {
                    "id_duplicado": dup_id,
                    "tabla_normalizada_afectada": "dim_empresas.csv",
                    "archivo_origen_csv": "CSV/Afiliados.csv",
                    "fila_origen_csv": int(dup["_fila_csv"]),
                    "tipo_duplicado": "Múltiples registros históricos de membresía",
                    "llave_negocio": f"id_empresa={emp_id}",
                    "id_empresa": emp_id,
                    "id_persona": None,
                    "id_evento": None,
                    "fecha_iso": f_afil_d or f_exp_d,
                    "regla_identificacion": "id_empresa repetido en Afiliados.csv",
                    "detalle_primera_aparicion": (
                        f"ID={princ.get('ID de registro [anonimizado]')} | "
                        f"Estado={princ.get('Estado de la Membresía')}"
                    ),
                    "detalle_duplicado": (
                        f"ID={dup.get('ID de registro [anonimizado]')} | "
                        f"Estado={dup.get('Estado de la Membresía')}"
                    ),
                }
            )
            dup_crm_rows.append(
                {
                    "id_duplicado": dup_id,
                    "fila_duplicada_csv": int(dup["_fila_csv"]),
                    "fila_principal_csv": int(princ["_fila_csv"]),
                    "id_registro_principal": _clean_id(
                        princ.get("ID de registro [anonimizado]")
                    ),
                    "id_registro_duplicado": _clean_id(
                        dup.get("ID de registro [anonimizado]")
                    ),
                    "id_empresa": emp_id,
                    "estado_principal": _clean_text(princ.get("Estado")),
                    "estado_duplicado": _clean_text(dup.get("Estado")),
                    "estado_membresia_principal": _clean_text(
                        princ.get("Estado de la Membresía")
                    ),
                    "estado_membresia_duplicado": _clean_text(
                        dup.get("Estado de la Membresía")
                    ),
                    "tipo_membresia_principal": _clean_text(
                        princ.get("Tipo de Membresía")
                    ),
                    "tipo_membresia_duplicado": _clean_text(dup.get("Tipo de Membresía")),
                    "categoria_principal": _clean_text(
                        princ.get("Categoría de Membresía")
                    ),
                    "categoria_duplicada": _clean_text(dup.get("Categoría de Membresía")),
                    "fecha_afiliacion_principal": f_afil_p,
                    "fecha_afiliacion_duplicada": f_afil_d,
                    "fecha_expiracion_principal": f_exp_p,
                    "fecha_expiracion_duplicada": f_exp_d,
                }
            )

    df_af_princ = pd.DataFrame(principales_list).reset_index(drop=True)

    # 2. Leer consolidado_asistencia.csv (KAMs y seguimiento)
    df_ca = pd.read_csv(raw_dir / "consolidado_asistencia.csv", dtype=str)
    kam_nombres: dict[str, str] = {}
    kam_seguimiento_emp: dict[str, dict[str, Any]] = {}
    for _, r in df_ca.iterrows():
        k_id = _clean_kam_label(r.get("BD_KAM"))
        resp = _clean_text(r.get("Responsable"))
        if k_id and resp:
            kam_nombres[k_id] = resp
        ca_emp_id = _clean_id(r.get("Empresa"))
        if ca_emp_id:
            kam_seguimiento_emp[ca_emp_id] = {
                "kam_id": k_id,
                "asistio_segun_kam": (
                    _clean_text(r.get("Estado_Asistencia")) or ""
                ).lower()
                == "asistió",
                "eventos_reportados_kam": _parse_int(r.get("Eventos_Asistidos")) or 0,
            }

    # Mapas preliminares de KAM y nivel por empresa
    kam_por_empresa: dict[str, str] = {}
    nivel_por_empresa: dict[str, str | None] = {}
    for _, r in df_af_princ.iterrows():
        emp_id = str(r["_id_empresa"])
        kam_por_empresa[emp_id] = _clean_kam_label(
            r.get("Propietario de Empresa [anonimizado]")
        )
        nivel_por_empresa[emp_id] = _normalizar_nivel_membresia(
            _clean_text(r.get("Tipo de Membresía")),
            _clean_text(r.get("Categoría de Membresía")),
        )
    for emp_id, info in kam_seguimiento_emp.items():
        if emp_id not in kam_por_empresa:
            kam_por_empresa[emp_id] = info["kam_id"]

    # 3. Leer matriz general, eventos, asistencias, encuestas y movimientos CRM
    matriz_emp_ev, matriz_por_ev, matriz_por_emp = _leer_matriz_general(raw_dir)
    df_eventos, df_asistencias = _construir_eventos_y_asistencias(
        raw_dir, kam_por_empresa, matriz_emp_ev, matriz_por_ev, duplicados_rows
    )
    df_encuestas = _construir_encuestas(raw_dir)
    df_movimientos, nuevos_per_emp, nuevos_per_fecha = _construir_movimientos_crm(
        raw_dir, kam_por_empresa, nivel_por_empresa
    )

    # 4. Construir dim_empresas completa (CRM + empresas externas en hechos)
    asist_por_emp = (
        df_asistencias[df_asistencias["id_empresa"].notna()]
        .groupby("id_empresa")
        .agg(
            eventos_asistidos_reales=("id_evento", "nunique"),
            participaciones_reales=("id_asistencia", "count"),
        )
        .to_dict(orient="index")
        if not df_asistencias.empty
        else {}
    )
    enc_por_emp = (
        df_encuestas[df_encuestas["id_empresa"].notna()]
        .groupby("id_empresa")["id_respuesta"]
        .count()
        .to_dict()
        if not df_encuestas.empty
        else {}
    )

    # Subsectores extra desde informe_subsectores.csv si falta en Afiliados.csv
    subsector_extra: dict[str, str] = {}
    sub_path = raw_dir / "informe_subsectores.csv"
    if sub_path.exists():
        df_sub = pd.read_csv(sub_path, skiprows=6, dtype=str)
        for _, r in df_sub.iterrows():
            e_id = _clean_id(r.iloc[0]) if len(r) > 0 else None
            sub_val = _clean_text(r.iloc[1]) if len(r) > 1 else None
            if e_id and e_id.startswith("EMP-") and sub_val:
                subsector_extra[e_id] = sub_val

    empresas_rows: list[dict[str, Any]] = []
    empresas_vistas: set[str] = set()

    for _, r in df_af_princ.iterrows():
        emp_id = str(r["_id_empresa"])
        empresas_vistas.add(emp_id)
        tipo_orig = _clean_text(r.get("Tipo de Membresía"))
        cat_orig = _clean_text(r.get("Categoría de Membresía"))
        est_emp = _clean_text(r.get("Estado"))
        est_memb = _clean_text(r.get("Estado de la Membresía"))
        kam_val = _clean_kam_label(r.get("Propietario de Empresa [anonimizado]"))
        ult_act_raw = _clean_text(r.get("Hora de la última actividad"))
        cam_reg_raw = _clean_text(r.get("Cambiar hora de registro"))
        seg_info = kam_seguimiento_emp.get(emp_id, {})
        asist_info = asist_por_emp.get(emp_id, {})
        ev_reales = int(asist_info.get("eventos_asistidos_reales", 0))
        part_reales = int(asist_info.get("participaciones_reales", 0))
        ev_mat = int(matriz_por_emp.get(emp_id, 0))
        ciudad = _clean_text(r.get("Ciudad")) or _clean_text(
            r.get("Ciudad de facturación")
        )
        region = _clean_text(r.get("Departamento")) or _clean_text(r.get("Región"))
        etiqueta = (_clean_text(r.get("Etiqueta")) or "").lower()

        empresas_rows.append(
            {
                "id_empresa": emp_id,
                "id_registro_crm": _clean_id(r.get("ID de registro [anonimizado]")),
                "kam_id": kam_val,
                "es_empresa_activa": (est_emp or "").lower() == "activo",
                "es_membresia_activa": (est_memb or "").lower() == "activo",
                "estado_membresia_detalle": est_memb or "Sin dato",
                "segmento_membresia": _normalizar_segmento_membresia(tipo_orig, cat_orig),
                "nivel_membresia": _normalizar_nivel_membresia(tipo_orig, cat_orig),
                "tipo_membresia_original": tipo_orig,
                "categoria_membresia_original": cat_orig,
                "sector_economico": _clean_text(r.get("Sector Económico")),
                "subsector_economico": _clean_text(
                    r.get("Subsector Económico [anonimizado]")
                )
                or subsector_extra.get(emp_id),
                "tamano_empresa": _clean_text(r.get("Tamaño de la Empresa")),
                "rango_empleados": _clean_text(r.get("Cantidad de Empleados")),
                "porcentaje_mujeres_num": _parse_float(
                    r.get("% de Mujeres en la Compañía")
                ),
                "ciudad": ciudad,
                "region_departamento": region,
                "pais": _clean_text(r.get("País de facturación")),
                "fecha_afiliacion": _parse_fecha_es(r.get("Fecha de Afiliación")),
                "fecha_expiracion": _parse_fecha_es(
                    r.get("Fecha de Expiración Afiliación")
                ),
                "fecha_miembro_desde": _parse_fecha_es(r.get("Miembro Desde el")),
                "fecha_ultima_actividad": _parse_fecha_es(ult_act_raw),
                "fecha_hora_ultima_actividad": ult_act_raw,
                "fecha_cambio_registro": _parse_fecha_es(cam_reg_raw),
                "fecha_hora_cambio_registro": cam_reg_raw,
                "es_independiente": _flag_bool(r.get("Independiente")),
                "es_registro_prueba": "prueba" in etiqueta,
                "bloqueado_crm": _flag_bool(r.get("Locked")),
                "vinculado_comunidades": _flag_bool(r.get("Vinculado a Comunidades")),
                "pilar_hr_estrategico": _flag_bool(r.get("HR Estratégico")),
                "pilar_mas_que_salario": _flag_bool(r.get("Mas que un Salario")),
                "pilar_talento_que_elige": _flag_bool(r.get("Talento que Elige")),
                "pilar_gente_que_crece": _flag_bool(r.get("Gente que Crece")),
                "comunidad_mujeres_hr": _flag_bool(r.get("Mujeres HR")),
                "es_influenciador": _flag_bool(r.get("Influenciador")),
                "en_crm_afiliados": True,
                "en_seguimiento_kam": emp_id in kam_seguimiento_emp,
                "asistio_segun_kam": bool(seg_info.get("asistio_segun_kam", False)),
                "en_matriz_general": emp_id in matriz_por_emp,
                "asistio_eventos_2026": ev_reales > 0,
                "eventos_asistidos_reales": ev_reales,
                "participaciones_reales": part_reales,
                "eventos_reportados_kam": int(seg_info.get("eventos_reportados_kam", 0)),
                "eventos_reportados_matriz": ev_mat,
                "respuestas_encuestas": int(enc_por_emp.get(emp_id, 0)),
            }
        )

    # Empresas que solo aparecen en asistencias, encuestas, movimientos o matriz
    externas: set[str] = set()
    for serie in (
        (
            df_asistencias["id_empresa"]
            if not df_asistencias.empty
            else pd.Series(dtype=str)
        ),
        df_encuestas["id_empresa"] if not df_encuestas.empty else pd.Series(dtype=str),
        (
            df_movimientos["id_empresa"]
            if not df_movimientos.empty
            else pd.Series(dtype=str)
        ),
    ):
        for val in serie.dropna().unique():
            externas.add(str(val))
    externas.update(kam_seguimiento_emp.keys())
    externas.update(matriz_por_emp.keys())

    mov_kam_map = (
        df_movimientos.dropna(subset=["id_empresa"])
        .set_index("id_empresa")["kam_id"]
        .to_dict()
        if not df_movimientos.empty
        else {}
    )
    for emp_id in sorted(externas - empresas_vistas):
        seg_info = kam_seguimiento_emp.get(emp_id, {})
        asist_info = asist_por_emp.get(emp_id, {})
        ev_reales = int(asist_info.get("eventos_asistidos_reales", 0))
        part_reales = int(asist_info.get("participaciones_reales", 0))
        ev_mat = int(matriz_por_emp.get(emp_id, 0))
        kam_ext = seg_info.get("kam_id") or mov_kam_map.get(emp_id) or "Sin asignar"
        empresas_rows.append(
            {
                "id_empresa": emp_id,
                "id_registro_crm": None,
                "kam_id": kam_ext,
                "es_empresa_activa": False,
                "es_membresia_activa": False,
                "estado_membresia_detalle": "Sin membresía en CRM",
                "segmento_membresia": None,
                "nivel_membresia": None,
                "tipo_membresia_original": None,
                "categoria_membresia_original": None,
                "sector_economico": None,
                "subsector_economico": subsector_extra.get(emp_id),
                "tamano_empresa": None,
                "rango_empleados": None,
                "porcentaje_mujeres_num": None,
                "ciudad": None,
                "region_departamento": None,
                "pais": None,
                "fecha_afiliacion": None,
                "fecha_expiracion": None,
                "fecha_miembro_desde": None,
                "fecha_ultima_actividad": None,
                "fecha_hora_ultima_actividad": None,
                "fecha_cambio_registro": None,
                "fecha_hora_cambio_registro": None,
                "es_independiente": False,
                "es_registro_prueba": False,
                "bloqueado_crm": False,
                "vinculado_comunidades": False,
                "pilar_hr_estrategico": False,
                "pilar_mas_que_salario": False,
                "pilar_talento_que_elige": False,
                "pilar_gente_que_crece": False,
                "comunidad_mujeres_hr": False,
                "es_influenciador": False,
                "en_crm_afiliados": False,
                "en_seguimiento_kam": emp_id in kam_seguimiento_emp,
                "asistio_segun_kam": bool(seg_info.get("asistio_segun_kam", False)),
                "en_matriz_general": emp_id in matriz_por_emp,
                "asistio_eventos_2026": ev_reales > 0,
                "eventos_asistidos_reales": ev_reales,
                "participaciones_reales": part_reales,
                "eventos_reportados_kam": int(seg_info.get("eventos_reportados_kam", 0)),
                "eventos_reportados_matriz": ev_mat,
                "respuestas_encuestas": int(enc_por_emp.get(emp_id, 0)),
            }
        )

    df_empresas = (
        pd.DataFrame(empresas_rows).sort_values("id_empresa").reset_index(drop=True)
    )

    # 5. Construir dim_personas consolidando asistencias, encuestas y nuevos_afiliados
    personas_ids: set[str] = set()
    if not df_asistencias.empty:
        personas_ids.update(df_asistencias["id_persona"].dropna().astype(str).unique())
    if not df_encuestas.empty:
        personas_ids.update(df_encuestas["id_persona"].dropna().astype(str).unique())
    personas_ids.update(nuevos_per_emp.keys())

    asist_per_grp = (
        df_asistencias.groupby("id_persona")
        .agg(
            id_empresa_asist=(
                "id_empresa",
                lambda s: s.dropna().iloc[0] if len(s.dropna()) else None,
            ),
            nivel_cargo=(
                "nivel_cargo",
                lambda s: s.dropna().iloc[0] if len(s.dropna()) else None,
            ),
            ciudad_asist=(
                "ciudad_evento",
                lambda s: s.dropna().iloc[0] if len(s.dropna()) else None,
            ),
            eventos_asistidos_2026=("id_evento", "nunique"),
            fecha_primer_evento_2026=("fecha_evento", "min"),
            fecha_ultimo_evento_2026=("fecha_evento", "max"),
        )
        .to_dict(orient="index")
        if not df_asistencias.empty
        else {}
    )
    enc_per_grp = (
        df_encuestas[df_encuestas["id_persona"].notna()]
        .groupby("id_persona")
        .agg(
            id_empresa_enc=(
                "id_empresa",
                lambda s: s.dropna().iloc[0] if len(s.dropna()) else None,
            ),
            ciudad_enc=(
                "ciudad",
                lambda s: s.dropna().iloc[0] if len(s.dropna()) else None,
            ),
            encuestas_presenciales=(
                "es_modalidad_presencial",
                lambda s: int(s.astype(bool).sum()),
            ),
            encuestas_virtuales=(
                "es_modalidad_presencial",
                lambda s: int((~s.astype(bool)).sum()),
            ),
        )
        .to_dict(orient="index")
        if not df_encuestas.empty
        else {}
    )

    personas_rows: list[dict[str, Any]] = []
    for pid in sorted(personas_ids):
        a_info = asist_per_grp.get(pid, {})
        e_info = enc_per_grp.get(pid, {})
        emp_princ = (
            a_info.get("id_empresa_asist")
            or e_info.get("id_empresa_enc")
            or nuevos_per_emp.get(pid)
        )
        ev_cnt = int(a_info.get("eventos_asistidos_2026", 0))
        enc_p = int(e_info.get("encuestas_presenciales", 0))
        enc_v = int(e_info.get("encuestas_virtuales", 0))
        personas_rows.append(
            {
                "id_persona": pid,
                "id_empresa_principal": emp_princ,
                "nivel_cargo": a_info.get("nivel_cargo"),
                "ciudad": a_info.get("ciudad_asist") or e_info.get("ciudad_enc"),
                "asistio_eventos_2026": ev_cnt > 0,
                "respondio_encuestas": (enc_p + enc_v) > 0,
                "es_afiliado_principal_nuevo": pid in nuevos_per_emp,
                "eventos_asistidos_2026": ev_cnt,
                "encuestas_presenciales": enc_p,
                "encuestas_virtuales": enc_v,
                "fecha_primer_evento_2026": a_info.get("fecha_primer_evento_2026"),
                "fecha_ultimo_evento_2026": a_info.get("fecha_ultimo_evento_2026"),
                "fecha_afiliacion_nueva": nuevos_per_fecha.get(pid),
            }
        )
    df_personas = pd.DataFrame(personas_rows)

    # 6. Construir dim_kams consolidando todos los KAMs observados
    sin_asig_vals = set(cfg.valores_origen_sin_asignar)
    kams_set: set[str] = set()
    for serie in (
        df_empresas["kam_id"],
        df_asistencias["kam_id"] if not df_asistencias.empty else pd.Series(dtype=str),
        df_movimientos["kam_id"] if not df_movimientos.empty else pd.Series(dtype=str),
    ):
        for val in serie.dropna().unique():
            val_str = str(val).strip()
            if val_str in sin_asig_vals:
                kams_set.add("Sin asignar (cuenta ACTHO)")
            else:
                kams_set.add(val_str)
    kams_set.add("Sin asignar (cuenta ACTHO)")

    kams_rows: list[dict[str, Any]] = []
    for k_id in sorted(kams_set):
        es_sin = k_id in sin_asig_vals
        mask_emp = (
            df_empresas["kam_id"].isin(sin_asig_vals)
            if es_sin
            else (df_empresas["kam_id"] == k_id)
        )
        sub_emp = df_empresas[mask_emp]
        sub_mov = (
            df_movimientos[
                (
                    df_movimientos["kam_id"].isin(sin_asig_vals)
                    if es_sin
                    else (df_movimientos["kam_id"] == k_id)
                )
            ]
            if not df_movimientos.empty
            else pd.DataFrame()
        )
        kams_rows.append(
            {
                "kam_id": k_id,
                "responsable_nombre": kam_nombres.get(
                    k_id, "Sin asignar" if es_sin else k_id
                ),
                "tiene_seguimiento_eventos": k_id in kam_nombres,
                "total_registros_afiliados": int(sub_emp["en_crm_afiliados"].sum()),
                "afiliados_activos": int(sub_emp["es_membresia_activa"].sum()),
                "cuentas_elite_premium": int(
                    sub_emp["nivel_membresia"].isin(["Elite", "Premium"]).sum()
                ),
                "empresas_seguimiento_asistencia": int(
                    sub_emp["en_seguimiento_kam"].sum()
                ),
                "empresas_que_asistieron": int(sub_emp["asistio_segun_kam"].sum()),
                "tratos_en_estado": (
                    int((sub_mov["tipo_movimiento"] == "Trato en Estado").sum())
                    if not sub_mov.empty
                    else 0
                ),
                "nuevas_afiliaciones_ult_2m": (
                    int(
                        (
                            sub_mov["tipo_movimiento"]
                            == "Nueva Afiliación (Últ. 2 Meses)"
                        ).sum()
                    )
                    if not sub_mov.empty
                    else 0
                ),
                "renovaciones_ult_2m": (
                    int(sub_mov["es_renovacion"].astype(bool).sum())
                    if not sub_mov.empty
                    else 0
                ),
            }
        )
    df_kams = pd.DataFrame(kams_rows)

    df_duplicados = pd.DataFrame(
        duplicados_rows,
        columns=[
            "id_duplicado",
            "tabla_normalizada_afectada",
            "archivo_origen_csv",
            "fila_origen_csv",
            "tipo_duplicado",
            "llave_negocio",
            "id_empresa",
            "id_persona",
            "id_evento",
            "fecha_iso",
            "regla_identificacion",
            "detalle_primera_aparicion",
            "detalle_duplicado",
        ],
    )
    df_dup_crm = pd.DataFrame(
        dup_crm_rows,
        columns=[
            "id_duplicado",
            "fila_duplicada_csv",
            "fila_principal_csv",
            "id_registro_principal",
            "id_registro_duplicado",
            "id_empresa",
            "estado_principal",
            "estado_duplicado",
            "estado_membresia_principal",
            "estado_membresia_duplicado",
            "tipo_membresia_principal",
            "tipo_membresia_duplicado",
            "categoria_principal",
            "categoria_duplicada",
            "fecha_afiliacion_principal",
            "fecha_afiliacion_duplicada",
            "fecha_expiracion_principal",
            "fecha_expiracion_duplicada",
        ],
    )

    salidas = {
        "dim_empresas": df_empresas,
        "dim_personas": df_personas,
        "dim_eventos": df_eventos,
        "dim_kams": df_kams,
        "fact_asistencias": df_asistencias,
        "fact_encuestas_satisfaccion": df_encuestas,
        "fact_movimientos_crm": df_movimientos,
    }
    for nombre, df_out in salidas.items():
        df_out.to_csv(
            cfg.origen_normalizados_dir / f"{nombre}.csv",
            index=False,
            encoding="utf-8-sig",
        )

    df_duplicados.to_csv(
        cfg.origen_duplicados_dir / "registros_duplicados.csv",
        index=False,
        encoding="utf-8-sig",
    )
    df_dup_crm.to_csv(
        cfg.origen_duplicados_dir / "duplicados_afiliados_crm.csv",
        index=False,
        encoding="utf-8-sig",
    )

    logger.info(
        "Normalizados generados desde %s: empresas=%d, personas=%d, eventos=%d, "
        "kams=%d, asistencias=%d, encuestas=%d, movimientos=%d, duplicados=%d",
        raw_dir,
        len(df_empresas),
        len(df_personas),
        len(df_eventos),
        len(df_kams),
        len(df_asistencias),
        len(df_encuestas),
        len(df_movimientos),
        len(df_duplicados),
    )
    return {
        **salidas,
        "registros_duplicados": df_duplicados,
        "duplicados_afiliados_crm": df_dup_crm,
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    construir_normalizados_desde_raw()
