"""Suite de pruebas automatizadas para el modelo dimensional Medallion ACTHO 360."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.modules.eda import (
    cargar_configuracion,
    ejecutar_pipeline_completo,
    guardar_tabla_medallion,
)


def _fila_empresa_sintetica(
    id_emp: str,
    id_crm: str | None,
    kam_id: str,
    activa: bool,
    estado: str,
    *,
    f_afil: str | None = None,
    f_exp: str | None = None,
    en_crm: bool = True,
) -> dict[str, Any]:
    """Crea un diccionario de empresa sintética con todos los atributos requeridos.

    Args:
        id_emp: Identificador de la empresa.
        id_crm: Identificador del registro en CRM.
        kam_id: Identificador o etiqueta de la ejecutiva KAM.
        activa: Indicador de empresa y membresía activa.
        estado: Detalle del estado de membresía.
        f_afil: Fecha de afiliación ISO.
        f_exp: Fecha de expiración ISO.
        en_crm: Indicador de presencia en CRM.

    Returns:
        Diccionario completo para dim_empresas.csv.

    """
    return {
        "id_empresa": id_emp,
        "id_registro_crm": id_crm,
        "kam_id": kam_id,
        "es_empresa_activa": activa,
        "es_membresia_activa": activa,
        "estado_membresia_detalle": estado,
        "segmento_membresia": "Corporativa / Empresa",
        "nivel_membresia": "Premium" if activa else "Estándar",
        "tipo_membresia_original": "Empresa",
        "categoria_membresia_original": "Premium" if activa else "Estándar",
        "sector_economico": "Tecnología",
        "subsector_economico": "Software",
        "tamano_empresa": "Grande",
        "rango_empleados": "201-1.000",
        "porcentaje_mujeres_num": 45,
        "ciudad": "Bogotá",
        "region_departamento": "Bogotá D.C.",
        "pais": "Colombia",
        "fecha_afiliacion": f_afil,
        "fecha_expiracion": f_exp,
        "fecha_miembro_desde": "2020-01-01" if en_crm else None,
        "fecha_ultima_actividad": "2026-10-15" if en_crm else None,
        "fecha_hora_ultima_actividad": "2026-10-15 10:00:00" if en_crm else None,
        "fecha_cambio_registro": "2026-10-15" if en_crm else None,
        "fecha_hora_cambio_registro": "2026-10-15 10:00:00" if en_crm else None,
        "es_independiente": False,
        "es_registro_prueba": False,
        "bloqueado_crm": False,
        "vinculado_comunidades": activa,
        "pilar_hr_estrategico": activa,
        "pilar_mas_que_salario": False,
        "pilar_talento_que_elige": activa,
        "pilar_gente_que_crece": False,
        "comunidad_mujeres_hr": False,
        "es_influenciador": False,
        "en_crm_afiliados": en_crm,
        "en_seguimiento_kam": activa,
        "asistio_segun_kam": activa,
        "en_matriz_general": activa,
        "asistio_eventos_2026": True,
        "eventos_asistidos_reales": 2 if activa else 0,
        "participaciones_reales": 2 if activa else 0,
        "eventos_reportados_kam": 2 if activa else 0,
        "eventos_reportados_matriz": 2 if activa else 0,
        "respuestas_encuestas": 1 if activa else 0,
    }


def _crear_dimensiones_sinteticas(norm_dir: Path, dup_dir: Path) -> None:
    """Genera las dimensiones sintéticas (KAMs, empresas, personas, eventos).

    Args:
        norm_dir: Directorio temporal de archivos normalizados.
        dup_dir: Directorio temporal de archivos duplicados.

    """
    pd.DataFrame(
        [
            {
                "kam_id": "KAM A",
                "responsable_nombre": "Paula",
                "tiene_seguimiento_eventos": True,
                "total_registros_afiliados": 10,
                "afiliados_activos": 8,
                "cuentas_elite_premium": 3,
                "empresas_seguimiento_asistencia": 8,
                "empresas_que_asistieron": 6,
                "tratos_en_estado": 1,
                "nuevas_afiliaciones_ult_2m": 1,
                "renovaciones_ult_2m": 1,
            },
            {
                "kam_id": "KAM B",
                "responsable_nombre": "Priscilla",
                "tiene_seguimiento_eventos": True,
                "total_registros_afiliados": 12,
                "afiliados_activos": 9,
                "cuentas_elite_premium": 2,
                "empresas_seguimiento_asistencia": 9,
                "empresas_que_asistieron": 4,
                "tratos_en_estado": 2,
                "nuevas_afiliaciones_ult_2m": 1,
                "renovaciones_ult_2m": 1,
            },
            {
                "kam_id": "Sin asignar (cuenta ACTHO)",
                "responsable_nombre": "Corporativo",
                "tiene_seguimiento_eventos": False,
                "total_registros_afiliados": 5,
                "afiliados_activos": 1,
                "cuentas_elite_premium": 0,
                "empresas_seguimiento_asistencia": 0,
                "empresas_que_asistieron": 0,
                "tratos_en_estado": 1,
                "nuevas_afiliaciones_ult_2m": 0,
                "renovaciones_ult_2m": 0,
            },
        ]
    ).to_csv(norm_dir / "dim_kams.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            _fila_empresa_sintetica(
                "EMP-0001",
                "R-0001",
                "KAM A",
                True,
                "Activo",
                f_afil="2024-01-15",
                f_exp="2026-12-31",
            ),
            _fila_empresa_sintetica(
                "EMP-0002",
                "R-0002",
                "KAM B",
                True,
                "Activo",
                f_afil=None,
                f_exp="2026-09-30",
            ),
            _fila_empresa_sintetica(
                "EMP-0174",
                "R-0175",
                "Sin asignar (cuenta ACTHO)",
                False,
                "Cancelado",
                f_afil="2022-03-04",
                f_exp="2021-12-31",
            ),
            _fila_empresa_sintetica(
                "EMP-1500",
                None,
                "Sin asignar",
                False,
                "Sin membresía en CRM",
                en_crm=False,
            ),
        ]
    ).to_csv(norm_dir / "dim_empresas.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "id_duplicado": "DUP-0001",
                "fila_duplicada_csv": 10,
                "fila_principal_csv": 5,
                "id_registro_principal": "R-0001",
                "id_registro_duplicado": "R-0001-OLD",
                "id_empresa": "EMP-0001",
                "estado_principal": "Activo",
                "estado_duplicado": "Inactivo",
                "estado_membresia_principal": "Activo",
                "estado_membresia_duplicado": "Cancelado",
                "tipo_membresia_principal": "Empresa",
                "tipo_membresia_duplicado": "Empresa",
                "categoria_principal": "Premium",
                "categoria_duplicada": "Estándar",
                "fecha_afiliacion_principal": "2024-01-15",
                "fecha_afiliacion_duplicada": "2021-01-15",
                "fecha_expiracion_principal": "2026-12-31",
                "fecha_expiracion_duplicada": "2023-12-31",
            },
        ]
    ).to_csv(
        dup_dir / "duplicados_afiliados_crm.csv",
        index=False,
        encoding="utf-8-sig",
    )

    pd.DataFrame(
        [
            {
                "id_persona": "P-0001",
                "id_empresa_principal": "EMP-0001",
                "nivel_cargo": "Dirección / Gerencia",
                "ciudad": "Bogotá",
                "asistio_eventos_2026": True,
                "respondio_encuestas": True,
                "es_afiliado_principal_nuevo": False,
                "eventos_asistidos_2026": 2,
                "encuestas_presenciales": 1,
                "encuestas_virtuales": 0,
                "fecha_primer_evento_2026": "2026-03-17",
                "fecha_ultimo_evento_2026": "2026-09-16",
                "fecha_afiliacion_nueva": None,
            },
            {
                "id_persona": "P-0002",
                "id_empresa_principal": None,
                "nivel_cargo": "Profesional / Analista / Consultor",
                "ciudad": "Cali",
                "asistio_eventos_2026": True,
                "respondio_encuestas": False,
                "es_afiliado_principal_nuevo": False,
                "eventos_asistidos_2026": 1,
                "encuestas_presenciales": 0,
                "encuestas_virtuales": 0,
                "fecha_primer_evento_2026": "2026-08-27",
                "fecha_ultimo_evento_2026": "2026-08-27",
                "fecha_afiliacion_nueva": None,
            },
        ]
    ).to_csv(norm_dir / "dim_personas.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "id_evento": 1,
                "archivo_csv": "MARZO 17.csv",
                "fecha_evento": "2026-03-17",
                "fecha_inicio_evento": "2026-03-17",
                "fecha_fin_evento": "2026-03-20",
                "periodo_mes_iso": "2026-03",
                "nombre_evento": "Semana del Talento",
                "linea_oferta_2027": "Evento grande",
                "experiencia_detalle": "Congreso",
                "modalidad": "Presencial",
                "es_presencial": True,
                "tiene_asistentes_registrados": True,
                "total_asistentes_archivo": 2,
                "empresas_unicas_archivo": 2,
                "personas_unicas_archivo": 2,
                "total_reportado_matriz_general": 1,
            },
            {
                "id_evento": 2,
                "archivo_csv": "SEPTIEMBRE 16.csv",
                "fecha_evento": "2026-09-16",
                "fecha_inicio_evento": "2026-09-16",
                "fecha_fin_evento": "2026-09-16",
                "periodo_mes_iso": "2026-09",
                "nombre_evento": "Foro Liderazgo",
                "linea_oferta_2027": "Foro",
                "experiencia_detalle": "Foro",
                "modalidad": "Virtual",
                "es_presencial": False,
                "tiene_asistentes_registrados": True,
                "total_asistentes_archivo": 2,
                "empresas_unicas_archivo": 1,
                "personas_unicas_archivo": 2,
                "total_reportado_matriz_general": 1,
            },
        ]
    ).to_csv(norm_dir / "dim_eventos.csv", index=False, encoding="utf-8-sig")


def _crear_hechos_y_duplicados_sinteticos(norm_dir: Path, dup_dir: Path) -> None:
    """Genera las tablas de hechos y los 122 registros duplicados sintéticos.

    Args:
        norm_dir: Directorio temporal de archivos normalizados.
        dup_dir: Directorio temporal de archivos duplicados.

    """
    pd.DataFrame(
        [
            {
                "id_asistencia": "A-00001",
                "id_evento": 1,
                "id_empresa": "EMP-0001",
                "id_persona": "P-0001",
                "kam_id": "KAM A",
                "fecha_evento": "2026-03-17",
                "periodo_mes_iso": "2026-03",
                "nivel_cargo": "Dirección / Gerencia",
                "ciudad_evento": "Bogotá",
                "cantidad_inscritos": 1,
                "es_afiliado": True,
                "tiene_costo": True,
                "autoriza_tratamiento_datos": True,
                "confirmado_ubicacion_principal": True,
                "reflejado_en_matriz_general": True,
                "conteo_empresa_matriz_general": 1,
            },
            {
                "id_asistencia": "A-00002",
                "id_evento": 2,
                "id_empresa": "EMP-0001",
                "id_persona": "P-0001",
                "kam_id": "KAM A",
                "fecha_evento": "2026-09-16",
                "periodo_mes_iso": "2026-09",
                "nivel_cargo": "Dirección / Gerencia",
                "ciudad_evento": "Bogotá",
                "cantidad_inscritos": 1,
                "es_afiliado": True,
                "tiene_costo": False,
                "autoriza_tratamiento_datos": True,
                "confirmado_ubicacion_principal": True,
                "reflejado_en_matriz_general": True,
                "conteo_empresa_matriz_general": 1,
            },
            {
                "id_asistencia": "A-00003",
                "id_evento": 1,
                "id_empresa": "EMP-1500",
                "id_persona": "P-0002",
                "kam_id": "Sin asignar",
                "fecha_evento": "2026-03-17",
                "periodo_mes_iso": "2026-03",
                "nivel_cargo": "Profesional / Analista / Consultor",
                "ciudad_evento": "Cali",
                "cantidad_inscritos": 1,
                "es_afiliado": False,
                "tiene_costo": False,
                "autoriza_tratamiento_datos": True,
                "confirmado_ubicacion_principal": True,
                "reflejado_en_matriz_general": False,
                "conteo_empresa_matriz_general": 0,
            },
            {
                "id_asistencia": "A-00004",
                "id_evento": 2,
                "id_empresa": None,
                "id_persona": "P-0002",
                "kam_id": "Sin asignar (cuenta ACTHO)",
                "fecha_evento": "2026-09-16",
                "periodo_mes_iso": "2026-09",
                "nivel_cargo": "Profesional / Analista / Consultor",
                "ciudad_evento": None,
                "cantidad_inscritos": 1,
                "es_afiliado": False,
                "tiene_costo": False,
                "autoriza_tratamiento_datos": True,
                "confirmado_ubicacion_principal": True,
                "reflejado_en_matriz_general": False,
                "conteo_empresa_matriz_general": 0,
            },
        ]
    ).to_csv(norm_dir / "fact_asistencias.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(
        [
            {
                "id_respuesta": "EP-0001",
                "modalidad_encuesta": "Presencial",
                "es_modalidad_presencial": True,
                "fecha_encuesta": "2026-03-18",
                "periodo_mes_iso": "2026-03",
                "fecha_hora_inicio": "2026-03-18 09:00:00",
                "fecha_hora_fin": "2026-03-18 09:02:00",
                "duracion_segundos": 120,
                "calif_locacion_o_plataforma": 5,
                "calif_convocatoria_publicidad": 5,
                "calif_conferencistas": 5,
                "calif_relevancia_temas": 5,
                "promedio_satisfaccion": 5.0,
                "temarios_sugeridos": "Inteligencia Artificial",
                "desea_recibir_actualizaciones": True,
                "id_persona": "P-0001",
                "id_empresa": "EMP-0001",
                "ciudad": "Bogotá",
                "empresa_en_crm": True,
                "metodo_asignacion_empresa": "Dominio del correo",
            },
            {
                "id_respuesta": "EV-0001",
                "modalidad_encuesta": "Virtual",
                "es_modalidad_presencial": False,
                "fecha_encuesta": "2026-09-17",
                "periodo_mes_iso": "2026-09",
                "fecha_hora_inicio": "2026-09-17 10:00:00",
                "fecha_hora_fin": "2026-09-17 10:01:30",
                "duracion_segundos": 90,
                "calif_locacion_o_plataforma": 3,
                "calif_convocatoria_publicidad": 3,
                "calif_conferencistas": 3,
                "calif_relevancia_temas": 3,
                "promedio_satisfaccion": 3.0,
                "temarios_sugeridos": "Reforma laboral",
                "desea_recibir_actualizaciones": True,
                "id_persona": "P-0002",
                "id_empresa": "EMP-0002",
                "ciudad": "Medellín",
                "empresa_en_crm": True,
                "metodo_asignacion_empresa": "Nombre de empresa",
            },
            {
                "id_respuesta": "EP-0002",
                "modalidad_encuesta": "Presencial",
                "es_modalidad_presencial": True,
                "fecha_encuesta": "2026-03-18",
                "periodo_mes_iso": "2026-03",
                "fecha_hora_inicio": "2026-03-18 11:00:00",
                "fecha_hora_fin": "2026-03-18 11:01:00",
                "duracion_segundos": 60,
                "calif_locacion_o_plataforma": 4,
                "calif_convocatoria_publicidad": 4,
                "calif_conferencistas": 5,
                "calif_relevancia_temas": 5,
                "promedio_satisfaccion": 4.5,
                "temarios_sugeridos": None,
                "desea_recibir_actualizaciones": False,
                "id_persona": None,
                "id_empresa": None,
                "ciudad": None,
                "empresa_en_crm": False,
                "metodo_asignacion_empresa": "Sin datos",
            },
        ]
    ).to_csv(
        norm_dir / "fact_encuestas_satisfaccion.csv",
        index=False,
        encoding="utf-8-sig",
    )

    pd.DataFrame(
        [
            {
                "tipo_movimiento": "Renovación (Últ. 2 Meses)",
                "es_cierre_facturado": True,
                "es_renovacion": True,
                "fecha_periodo_mes": "2026-09-01",
                "periodo_mes_iso": "2026-09",
                "fecha_cierre_o_factura": "2026-09-01",
                "fecha_expiracion_afiliacion": "2027-09-30",
                "fecha_exportacion_reporte": "2026-11-13",
                "kam_id": "KAM A",
                "id_empresa": "EMP-0001",
                "nivel_membresia": "Premium",
                "id_persona_contacto": "P-0001",
            },
            {
                "tipo_movimiento": "Trato en Estado",
                "es_cierre_facturado": False,
                "es_renovacion": False,
                "fecha_periodo_mes": None,
                "periodo_mes_iso": None,
                "fecha_cierre_o_factura": None,
                "fecha_expiracion_afiliacion": None,
                "fecha_exportacion_reporte": "2026-11-13",
                "kam_id": "Sin asignar",
                "id_empresa": "EMP-0002",
                "nivel_membresia": "Estándar",
                "id_persona_contacto": None,
            },
        ]
    ).to_csv(
        norm_dir / "fact_movimientos_crm.csv",
        index=False,
        encoding="utf-8-sig",
    )

    filas_dups: list[dict[str, Any]] = []
    for i in range(1, 123):
        es_hist = i == 1
        filas_dups.append(
            {
                "id_duplicado": f"DUP-{i:04d}",
                "tabla_normalizada_afectada": (
                    "dim_empresas.csv" if es_hist else "fact_asistencias.csv"
                ),
                "archivo_origen_csv": (
                    "CSV/Afiliados.csv" if es_hist else "Asistencia eventos/MARZO 17.csv"
                ),
                "fila_origen_csv": i + 10,
                "tipo_duplicado": (
                    "Múltiples registros históricos de membresía"
                    if es_hist
                    else (
                        "Duplicado exacto en el evento"
                        if i % 2 == 0
                        else "Misma persona con doble sesión"
                    )
                ),
                "llave_negocio": "id_empresa=EMP-0001",
                "id_empresa": "EMP-0001",
                "id_persona": None if es_hist else "P-0001",
                "id_evento": None if es_hist else 1,
                "fecha_iso": "2021-01-15" if es_hist else "2026-03-17",
                "regla_identificacion": "Auditoría de duplicados",
                "detalle_primera_aparicion": "ID=R-0001 | Estado=Activo",
                "detalle_duplicado": "ID=R-0001-OLD | Estado=Inactivo",
            }
        )
    pd.DataFrame(filas_dups).to_csv(
        dup_dir / "registros_duplicados.csv",
        index=False,
        encoding="utf-8-sig",
    )


def crear_fuentes_sinteticas(norm_dir: Path, dup_dir: Path) -> None:
    """Crea un conjunto de datos sintético representativo en tmp_path con 122 duplicados.

    Args:
        norm_dir: Directorio de tablas normalizadas de entrada.
        dup_dir: Directorio de registros duplicados.

    """
    norm_dir.mkdir(parents=True, exist_ok=True)
    dup_dir.mkdir(parents=True, exist_ok=True)
    _crear_dimensiones_sinteticas(norm_dir, dup_dir)
    _crear_hechos_y_duplicados_sinteticos(norm_dir, dup_dir)


@pytest.fixture(name="entorno_sintetico_etl", scope="module")
def fixture_entorno_sintetico_etl(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Any]:
    """Ejecuta el ETL sobre datos sintéticos en un directorio temporal independiente.

    Args:
        tmp_path_factory: Factoría de directorios temporales de pytest.

    Returns:
        Diccionario con la configuración y directorios generados.

    """
    base_tmp = tmp_path_factory.mktemp("actho360_test_env")
    norm_dir = base_tmp / "origen_normalizados"
    dup_dir = norm_dir / "duplicados"
    out_dir = base_tmp / "input"

    crear_fuentes_sinteticas(norm_dir, dup_dir)

    cfg = cargar_configuracion(
        origen_normalizados_override=norm_dir,
        origen_duplicados_override=dup_dir,
        salida_root_override=out_dir,
    )
    res_1 = ejecutar_pipeline_completo(cfg=cfg)
    return {
        "cfg": cfg,
        "res_1": res_1,
        "bronze_dir": cfg.bronze_dir,
        "silver_dir": cfg.silver_dir,
        "gold_dir": cfg.gold_dir,
        "audit_dir": cfg.audit_dir,
    }


def test_01_claves_primarias_unicas_y_no_nulas(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Valida que las claves primarias en Silver, Gold y Audit sean únicas y no nulas.

    Args:
        entorno_sintetico_etl: Fixture con las salidas del pipeline ETL.

    """
    s_dir: Path = entorno_sintetico_etl["silver_dir"]
    g_dir: Path = entorno_sintetico_etl["gold_dir"]
    a_dir: Path = entorno_sintetico_etl["audit_dir"]

    pks = [
        (s_dir / "dim_empresas.parquet", ["id_empresa"]),
        (s_dir / "dim_empresas_scd2.parquet", ["sk_empresa_scd2"]),
        (s_dir / "dim_personas.parquet", ["id_persona"]),
        (s_dir / "dim_eventos.parquet", ["id_evento"]),
        (s_dir / "dim_kams.parquet", ["kam_id"]),
        (s_dir / "fact_asistencias.parquet", ["id_asistencia"]),
        (s_dir / "fact_encuestas_satisfaccion.parquet", ["id_respuesta"]),
        (s_dir / "fact_movimientos_crm.parquet", ["id_movimiento"]),
        (
            g_dir / "agg_participacion_empresa.parquet",
            ["id_empresa", "periodo_analisis"],
        ),
        (
            g_dir / "agg_satisfaccion_encuestas.parquet",
            ["modalidad_encuesta", "periodo_mes_iso"],
        ),
        (g_dir / "agg_retencion_empresa.parquet", ["id_empresa"]),
        (a_dir / "audit_registros_duplicados.parquet", ["id_duplicado"]),
    ]
    for ruta, cols_pk in pks:
        df = pd.read_parquet(ruta)
        for col in cols_pk:
            assert df[col].isna().sum() == 0, f"Nulos en PK {col} de {ruta.name}"
        assert (
            df.duplicated(subset=cols_pk).sum() == 0
        ), f"Duplicados en PK {cols_pk} de {ruta.name}"


def test_02_integridad_referencial_y_homologacion_kam(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Valida integridad referencial al 100% y homologación a KAM-UNASSIGNED.

    Args:
        entorno_sintetico_etl: Fixture con las salidas del pipeline ETL.

    """
    s_dir: Path = entorno_sintetico_etl["silver_dir"]
    dim_emp = pd.read_parquet(s_dir / "dim_empresas.parquet")
    dim_per = pd.read_parquet(s_dir / "dim_personas.parquet")
    dim_ev = pd.read_parquet(s_dir / "dim_eventos.parquet")
    dim_kam = pd.read_parquet(s_dir / "dim_kams.parquet")
    fact_asist = pd.read_parquet(s_dir / "fact_asistencias.parquet")
    fact_enc = pd.read_parquet(s_dir / "fact_encuestas_satisfaccion.parquet")
    fact_mov = pd.read_parquet(s_dir / "fact_movimientos_crm.parquet")

    emp_set = set(dim_emp["id_empresa"].dropna())
    per_set = set(dim_per["id_persona"].dropna())
    ev_set = set(dim_ev["id_evento"].dropna())
    kam_set = set(dim_kam["kam_id"].dropna())

    assert "KAM-UNASSIGNED" in kam_set
    for df_t in (dim_kam, dim_emp, fact_asist, fact_mov):
        vals_k = set(df_t["kam_id"].dropna())
        assert "Sin asignar" not in vals_k
        assert "Sin asignar (cuenta ACTHO)" not in vals_k
        assert vals_k.issubset(kam_set)

    assert set(dim_per["id_empresa_principal"].dropna()).issubset(emp_set)
    assert set(fact_asist["id_empresa"].dropna()).issubset(emp_set)
    assert set(fact_asist["id_persona"].dropna()).issubset(per_set)
    assert set(fact_asist["id_evento"].dropna()).issubset(ev_set)
    assert set(fact_enc["id_persona"].dropna()).issubset(per_set)
    assert set(fact_enc["id_empresa"].dropna()).issubset(emp_set)
    assert set(fact_mov["id_empresa"].dropna()).issubset(emp_set)


def test_03_reconciliacion_bronze_silver_y_hashes_inmutables(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Valida reconciliación exacta Bronze vs Silver y registro de hashes SHA-256.

    Args:
        entorno_sintetico_etl: Fixture con las salidas del pipeline ETL.

    """
    a_dir: Path = entorno_sintetico_etl["audit_dir"]
    reconc = pd.read_parquet(a_dir / "audit_reconciliacion_origen_destino.parquet")
    hashes = pd.read_parquet(a_dir / "audit_hashes_fuentes_bronze.parquet")

    assert (reconc["Diferencia_Filas"] == 0).all()
    assert len(hashes) == 8
    assert hashes["integridad_verificada"].all()
    assert (hashes["sha256_origen"] == hashes["sha256_bronze"]).all()


def test_04_conservacion_122_registros_duplicados(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Verifica que los 122 registros de duplicados se conserven y clasifiquen.

    Args:
        entorno_sintetico_etl: Fixture con las salidas del pipeline ETL.

    """
    a_dir: Path = entorno_sintetico_etl["audit_dir"]
    audit_dup = pd.read_parquet(a_dir / "audit_registros_duplicados.parquet")
    assert len(audit_dup) == 122
    assert set(audit_dup["categoria_duplicidad"]).issubset(
        {
            "DUPLICADO_EXACTO",
            "DUPLICADO_NEGOCIO_HISTORICO_SCD2",
            "COINCIDENCIA_PARCIAL_ENTRE_FUENTES",
            "COINCIDENCIA_PARCIAL_DOBLE_INSCRIPCION_EVENTO",
        }
    )


def test_05_ausencia_nps_ficticio_y_separacion_satisfaccion_1_5(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Verifica que agg_satisfaccion_encuestas no invente NPS 0-10 ni id_evento.

    Args:
        entorno_sintetico_etl: Fixture con las salidas del pipeline ETL.

    """
    s_dir: Path = entorno_sintetico_etl["silver_dir"]
    g_dir: Path = entorno_sintetico_etl["gold_dir"]

    assert not (g_dir / "agg_satisfaccion_evento.csv").exists()
    assert (g_dir / "agg_satisfaccion_encuestas.parquet").exists()

    fact_enc = pd.read_parquet(s_dir / "fact_encuestas_satisfaccion.parquet")
    agg_sat = pd.read_parquet(g_dir / "agg_satisfaccion_encuestas.parquet")

    assert fact_enc["id_evento"].isna().all()
    assert fact_enc["pregunta_recomendacion_nps_0_10"].isna().all()
    assert agg_sat["nps_oficial_0_10"].isna().all()
    assert agg_sat["total_respuestas"].sum() == len(fact_enc)
    assert agg_sat["respuestas_anonimas_sin_persona"].sum() == int(
        fact_enc["id_persona"].isna().sum()
    )


def test_06_consistencia_agregaciones_gold_contra_silver(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Verifica consistencia de agg_participacion_empresa y agg_retencion_empresa.

    Args:
        entorno_sintetico_etl: Fixture con las salidas del pipeline ETL.

    """
    s_dir: Path = entorno_sintetico_etl["silver_dir"]
    g_dir: Path = entorno_sintetico_etl["gold_dir"]

    fact_asist = pd.read_parquet(s_dir / "fact_asistencias.parquet")
    agg_part = pd.read_parquet(g_dir / "agg_participacion_empresa.parquet")
    agg_ret = pd.read_parquet(g_dir / "agg_retencion_empresa.parquet")

    assert agg_part["total_asistencias"].sum() == int(
        fact_asist["id_empresa"].notna().sum()
    )
    sin_ev = agg_part[agg_part["total_eventos"] == 0]
    assert sin_ev["meses_sin_participacion"].isna().all()
    assert (
        sin_ev["estado_recencia_participacion"] == "SIN_PARTICIPACION_REGISTRADA"
    ).all()

    solapadas = agg_ret["es_membresia_vencida"] & agg_ret["es_proximo_vencimiento_90d"]
    assert not solapadas.any()
    assert (
        agg_ret["tipo_metodologia_riesgo"] == "REGLA_HEURISTICA_NEGOCIO_NO_PREDICTIVA"
    ).all()


def test_07_scd2_versiones_consecutivas_unica_actual_y_deteccion_fechas(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Valida versiones consecutivas 1..N, única versión actual y fechas inconsistentes.

    Args:
        entorno_sintetico_etl: Fixture con las salidas del pipeline ETL.

    """
    s_dir: Path = entorno_sintetico_etl["silver_dir"]
    scd2 = pd.read_parquet(s_dir / "dim_empresas_scd2.parquet")

    actuales_por_emp = scd2.groupby("id_empresa")["es_registro_actual"].sum()
    assert (actuales_por_emp == 1).all()

    for emp_id, grp in scd2.groupby("id_empresa"):
        esperadas = list(range(1, len(grp) + 1))
        assert (
            grp["version_registro"].tolist() == esperadas
        ), f"Versiones no consecutivas en {emp_id}"

    emp_174 = scd2[scd2["id_empresa"] == "EMP-0174"].iloc[0]
    assert bool(emp_174["tiene_fechas_inconsistentes"]) is True
    assert (
        emp_174["clasificacion_historia_scd2"] == "FECHA_INCONSISTENTE_INICIO_MAYOR_FIN"
    )

    emp_002 = scd2[scd2["id_empresa"] == "EMP-0002"].iloc[0]
    assert pd.isna(emp_002["fecha_inicio_vigencia"])
    assert emp_002["clasificacion_historia_scd2"] == "HISTORIA_PARCIAL_SIN_FECHA_INICIO"


def test_08_idempotencia_comparacion_real_dataframes_y_proteccion_bronze(
    entorno_sintetico_etl: dict[str, Any],
) -> None:
    """Verifica que dos ejecuciones produzcan DataFrames idénticos y protejan Bronze.

    Args:
        entorno_sintetico_etl: Fixture con las salidas del pipeline ETL.

    """
    cfg = entorno_sintetico_etl["cfg"]
    s_dir: Path = entorno_sintetico_etl["silver_dir"]
    g_dir: Path = entorno_sintetico_etl["gold_dir"]

    tablas_silver = [
        "dim_kams",
        "dim_empresas",
        "dim_empresas_scd2",
        "dim_personas",
        "dim_eventos",
        "fact_asistencias",
        "fact_encuestas_satisfaccion",
        "fact_movimientos_crm",
    ]
    tablas_gold = [
        "agg_participacion_empresa",
        "agg_satisfaccion_encuestas",
        "agg_retencion_empresa",
    ]

    snap_1_silver = {t: pd.read_parquet(s_dir / f"{t}.parquet") for t in tablas_silver}
    snap_1_gold = {t: pd.read_parquet(g_dir / f"{t}.parquet") for t in tablas_gold}

    res_2 = ejecutar_pipeline_completo(cfg=cfg)
    assert (
        res_2["hashes_bronze"]["accion_bronze"]
        == "CONSERVADO_SIN_SOBRESCRIBIR_HASH_IDENTICO"
    ).all()

    for tabla in tablas_silver:
        df_2 = pd.read_parquet(s_dir / f"{tabla}.parquet")
        pd.testing.assert_frame_equal(snap_1_silver[tabla], df_2, check_exact=True)

    for tabla in tablas_gold:
        df_2 = pd.read_parquet(g_dir / f"{tabla}.parquet")
        pd.testing.assert_frame_equal(snap_1_gold[tabla], df_2, check_exact=True)


def test_09_portabilidad_rutas_y_configuracion_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifica portabilidad de rutas y que por defecto las capas apunten a input/.

    Args:
        tmp_path: Directorio temporal de pytest.
        monkeypatch: Utilidad de pytest para modificar el directorio de trabajo.

    """
    cfg_default = cargar_configuracion()
    assert cfg_default.salida_root_dir.name == "input"
    assert cfg_default.bronze_dir == cfg_default.salida_root_dir / "bronze"
    assert cfg_default.silver_dir == cfg_default.salida_root_dir / "silver"
    assert cfg_default.gold_dir == cfg_default.salida_root_dir / "gold"
    assert cfg_default.audit_dir == cfg_default.salida_root_dir / "audit"

    otro_cwd = tmp_path / "directorio_trabajo_externo"
    otro_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(otro_cwd)

    norm_dir = tmp_path / "datos_in"
    dup_dir = norm_dir / "duplicados"
    out_dir = tmp_path / "input"
    crear_fuentes_sinteticas(norm_dir, dup_dir)

    cfg = cargar_configuracion(
        origen_normalizados_override=norm_dir,
        origen_duplicados_override=dup_dir,
        salida_root_override=out_dir,
    )
    res = ejecutar_pipeline_completo(cfg=cfg)
    assert (res["reconciliacion"]["Diferencia_Filas"] == 0).all()


def test_10_generacion_lectura_csv_parquet_y_reporte_fallo_parquet(
    entorno_sintetico_etl: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica lectura de CSV/Parquet y que un fallo en Parquet lance RuntimeError.

    Args:
        entorno_sintetico_etl: Fixture con las salidas del pipeline ETL.
        tmp_path: Directorio temporal de pytest.
        monkeypatch: Utilidad de pytest para simular fallos.

    """
    s_dir: Path = entorno_sintetico_etl["silver_dir"]
    for parquet_file in s_dir.glob("*.parquet"):
        csv_file = s_dir / f"{parquet_file.stem}.csv"
        assert csv_file.exists()
        df_p = pd.read_parquet(parquet_file)
        df_c = pd.read_csv(csv_file)
        assert len(df_p) == len(df_c)

    def fake_to_parquet(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("Fallo simulado de motor Parquet")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fake_to_parquet)
    errores_log: list[dict[str, Any]] = []
    with pytest.raises(RuntimeError, match="Error al generar archivo Parquet"):
        guardar_tabla_medallion(
            pd.DataFrame({"a": [1]}),
            tmp_path,
            "tabla_fallida",
            registro_errores=errores_log,
        )
    assert len(errores_log) == 1
    assert errores_log[0]["tabla"] == "tabla_fallida"
