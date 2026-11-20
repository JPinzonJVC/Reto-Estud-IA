"""Gestión de bitácoras de auditoría, rechazados, calidad y reconciliación Medallion."""

import json
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from app.modules.eda.bronze import guardar_tabla_medallion
from app.modules.eda.config import ConfiguracionETL


class BitacoraAuditoria:
    """Acumulador de cargas ETL, rechazados, errores e incidencias de calidad.

    Attributes:
        run_id: Identificador único de la ejecución ETL.
        fecha_corte: Fecha de corte del modelo analítico.
        registros_calidad: Lista de incidencias de calidad registradas.
        registros_cargas: Lista de ejecuciones de carga por tabla.
        registros_rechazados: Lista de registros rechazados con su motivo.
        errores: Lista de errores capturados durante la ejecución.

    """

    def __init__(self, run_id: str, fecha_corte: str) -> None:
        """Inicializa la bitácora de auditoría para una ejecución ETL.

        Args:
            run_id: Identificador único de la ejecución.
            fecha_corte: Fecha de corte configurada.

        """
        self.run_id: str = run_id
        self.fecha_corte: str = fecha_corte
        self.registros_calidad: list[dict[str, Any]] = []
        self.registros_cargas: list[dict[str, Any]] = []
        self.registros_rechazados: list[dict[str, Any]] = []
        self.errores: list[str] = []

    def registrar_carga(
        self,
        fuente: str,
        t_ini: str,
        *,
        leidos: int,
        proc: int,
        ins: int,
        act: int,
        rech: int = 0,
    ) -> None:
        """Registra la ejecución de una etapa de carga entre capas Medallion.

        Args:
            fuente: Descripción del flujo origen -> destino.
            t_ini: Marca temporal de inicio.
            leidos: Cantidad de registros leídos.
            proc: Cantidad de registros procesados.
            ins: Cantidad de registros insertados.
            act: Cantidad de registros actualizados u homologados.
            rech: Cantidad de registros rechazados.

        """
        self.registros_cargas.append(
            {
                "id_ejecucion": self.run_id,
                "fuente": fuente,
                "fecha_inicio": t_ini,
                "fecha_finalizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "registros_leidos": int(leidos),
                "registros_procesados": int(proc),
                "registros_insertados": int(ins),
                "registros_actualizados": int(act),
                "registros_rechazados": int(rech),
                "estado_ejecucion": "EXITOSO",
            }
        )

    def registrar_calidad(
        self,
        tabla: str,
        campo: str,
        *,
        tipo_inc: str,
        val_orig: str,
        val_corr: str,
        estado: str,
        cant: int,
    ) -> None:
        """Registra una regla o incidencia de calidad de datos aplicada.

        Args:
            tabla: Nombre de la tabla analizada.
            campo: Campo o conjunto de campos afectados.
            tipo_inc: Tipología de la inconsistencia o regla.
            val_orig: Descripción del valor original observado.
            val_corr: Acción o valor corregido aplicado.
            estado: Estado de resolución de la incidencia.
            cant: Cantidad de registros afectados.

        """
        idx = len(self.registros_calidad) + 1
        self.registros_calidad.append(
            {
                "id_incidencia": f"DQ-{idx:04d}",
                "tabla_analizada": tabla,
                "campo_afectado": campo,
                "tipo_inconsistencia": tipo_inc,
                "registros_afectados": int(cant),
                "valor_original": val_orig,
                "valor_corregido": val_corr,
                "fecha_corte_modelo": self.fecha_corte,
                "estado_resolucion": estado,
            }
        )

    def registrar_rechazo(
        self,
        tabla: str,
        archivo_origen: str,
        motivo: str,
        payload: dict[str, Any],
    ) -> None:
        """Conserva un registro rechazado junto con su motivo y fuente Bronze.

        Args:
            tabla: Tabla Silver donde se detectó el rechazo.
            archivo_origen: Archivo Bronze de origen.
            motivo: Motivo detallado del rechazo.
            payload: Diccionario con los datos originales del registro.

        """
        idx = len(self.registros_rechazados) + 1
        serializado = json.dumps(payload, default=str, ensure_ascii=False)
        self.registros_rechazados.append(
            {
                "id_rechazo": f"REJ-{idx:04d}",
                "id_ejecucion": self.run_id,
                "tabla_destino": tabla,
                "archivo_origen_bronze": archivo_origen,
                "motivo_rechazo": motivo,
                "registro_original_json": serializado,
                "fecha_corte_modelo": self.fecha_corte,
            }
        )


def filtrar_registros_rechazados(
    df: pd.DataFrame,
    tabla: str,
    pk_cols: list[str],
    archivo_origen: str,
    bitacora: BitacoraAuditoria,
) -> tuple[pd.DataFrame, int]:
    """Filtra y conserva en auditoría filas con claves primarias nulas o duplicadas.

    Args:
        df: DataFrame de entrada a validar.
        tabla: Nombre de la tabla Silver destino.
        pk_cols: Lista de columnas que conforman la clave primaria.
        archivo_origen: Nombre del archivo Bronze de origen.
        bitacora: Bitácora de auditoría activa.

    Returns:
        Tupla con el DataFrame válido depurado y la cantidad de filas rechazadas.

    """
    mask_pk_nula = df[pk_cols].isna().any(axis=1)
    for col in pk_cols:
        mask_vacia = df[col].astype(str).str.strip().isin(["", "nan", "None", "<NA>"])
        mask_pk_nula = mask_pk_nula | (df[col].isna() | mask_vacia)

    rechazados_cnt = 0
    if mask_pk_nula.any():
        for _, row in df[mask_pk_nula].iterrows():
            bitacora.registrar_rechazo(
                tabla=tabla,
                archivo_origen=archivo_origen,
                motivo=f"CLAVE_PRIMARIA_NULA_O_VACIA ({','.join(pk_cols)})",
                payload={str(k): v for k, v in row.to_dict().items()},
            )
            rechazados_cnt += 1

    df_valido = df[~mask_pk_nula].copy()
    mask_dup_pk = df_valido.duplicated(subset=pk_cols, keep="first")
    if mask_dup_pk.any():
        for _, row in df_valido[mask_dup_pk].iterrows():
            bitacora.registrar_rechazo(
                tabla=tabla,
                archivo_origen=archivo_origen,
                motivo=f"CLAVE_PRIMARIA_DUPLICADA ({','.join(pk_cols)})",
                payload={str(k): v for k, v in row.to_dict().items()},
            )
            rechazados_cnt += 1
        df_valido = df_valido[~mask_dup_pk].copy()

    return df_valido.reset_index(drop=True), rechazados_cnt


def _clasificar_categoria_duplicado(tipo: Any) -> str:
    """Clasifica el tipo de duplicado en una categoría estandarizada de auditoría.

    Args:
        tipo: Descripción original del tipo de duplicado.

    Returns:
        Categoría estandarizada de duplicidad.

    """
    texto = str(tipo).lower()
    if "exacto" in texto:
        return "DUPLICADO_EXACTO"
    if "histórico" in texto or "múltiples registros" in texto:
        return "DUPLICADO_NEGOCIO_HISTORICO_SCD2"
    if "simultáneamente" in texto or "2 portafolios" in texto or "dos filas" in texto:
        return "COINCIDENCIA_PARCIAL_ENTRE_FUENTES"
    return "COINCIDENCIA_PARCIAL_DOBLE_INSCRIPCION_EVENTO"


def _extraer_id_conservado(detalle: Any) -> str:
    """Extrae el identificador del registro conservado desde el detalle textual.

    Args:
        detalle: Texto descriptivo de la primera aparición.

    Returns:
        Identificador del registro principal conservado.

    """
    texto = str(detalle)
    for token in texto.replace("|", " ").replace(":", " ").split():
        if token.startswith(("R-", "A-", "EP-", "EV-", "EMP-")):
            return token.rstrip(",")
    return "VER_DETALLE_PRIMERA_APARICION"


def construir_audit_duplicados(
    df_dup_orig: pd.DataFrame,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> pd.DataFrame:
    """Construye y persiste la tabla audit_registros_duplicados.

    Args:
        df_dup_orig: DataFrame de duplicados leído desde Bronze.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría activa.

    Returns:
        DataFrame de auditoría de duplicados clasificados.

    """
    t0 = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_audit_dup = df_dup_orig.copy()
    df_audit_dup["categoria_duplicidad"] = df_audit_dup["tipo_duplicado"].apply(
        _clasificar_categoria_duplicado
    )
    df_audit_dup["id_registro_conservado"] = df_audit_dup[
        "detalle_primera_aparicion"
    ].apply(_extraer_id_conservado)
    df_audit_dup["fecha_deteccion"] = cfg.fecha_corte
    df_audit_dup["estado_revision"] = "DOCUMENTADO_EN_AUDITORIA"
    df_audit_dup["accion_aplicada"] = np.where(
        df_audit_dup["categoria_duplicidad"] == "DUPLICADO_NEGOCIO_HISTORICO_SCD2",
        "INCORPORADO_EN_DIM_EMPRESAS_SCD2",
        "CONSERVADO_EN_TABLA_HECHOS_CON_TRAZABILIDAD",
    )
    guardar_tabla_medallion(df_audit_dup, cfg.audit_dir, "audit_registros_duplicados")
    bitacora.registrar_carga(
        "bronze/registros_duplicados -> audit/audit_registros_duplicados",
        t0,
        leidos=len(df_dup_orig),
        proc=len(df_audit_dup),
        ins=len(df_audit_dup),
        act=0,
    )
    return df_audit_dup


def _fila_reconciliacion(
    tabla: str,
    df_b: pd.DataFrame,
    df_s: pd.DataFrame,
    explicacion: str,
    rechazados: int = 0,
) -> dict[str, Any]:
    """Crea un diccionario de reconciliación de conteos entre Bronze y Silver.

    Args:
        tabla: Nombre de la tabla reconciliada.
        df_b: DataFrame en la capa Bronze.
        df_s: DataFrame en la capa Silver/Audit.
        explicacion: Nota técnica de reconciliación.
        rechazados: Cantidad de filas rechazadas en Silver para esa tabla.

    Returns:
        Diccionario con conteos de filas, columnas y diferencias.

    """
    return {
        "Tabla": tabla,
        "Filas_Bronze": len(df_b),
        "Cols_Bronze": df_b.shape[1],
        "Filas_Silver": len(df_s),
        "Cols_Silver": df_s.shape[1],
        "Filas_Rechazadas": int(rechazados),
        "Diferencia_Filas": (len(df_s) + int(rechazados)) - len(df_b),
        "Explicacion_Reconciliacion": explicacion,
    }


def _construir_df_rechazados(bitacora: BitacoraAuditoria) -> pd.DataFrame:
    """Construye el DataFrame de registros rechazados con esquema fijo.

    Args:
        bitacora: Bitácora de auditoría con la lista de rechazados.

    Returns:
        DataFrame con las columnas de audit_registros_rechazados.

    """
    cols = [
        "id_rechazo",
        "id_ejecucion",
        "tabla_destino",
        "archivo_origen_bronze",
        "motivo_rechazo",
        "registro_original_json",
        "fecha_corte_modelo",
    ]
    if not bitacora.registros_rechazados:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(bitacora.registros_rechazados)[cols]


def persistir_auditoria_final(
    bronze: dict[str, pd.DataFrame],
    silver: dict[str, pd.DataFrame],
    df_audit_dup: pd.DataFrame,
    cfg: ConfiguracionETL,
    bitacora: BitacoraAuditoria,
) -> dict[str, pd.DataFrame]:
    """Persiste las tablas de calidad, rechazados, reconciliación y cargas.

    Args:
        bronze: Diccionario de DataFrames de la capa Bronze.
        silver: Diccionario de DataFrames de la capa Silver.
        df_audit_dup: DataFrame de auditoría de duplicados.
        cfg: Configuración del pipeline ETL Medallion.
        bitacora: Bitácora de auditoría con incidencias, rechazados y cargas.

    Returns:
        Diccionario con los DataFrames de auditoría generados.

    """
    df_audit_calidad = pd.DataFrame(bitacora.registros_calidad)
    guardar_tabla_medallion(df_audit_calidad, cfg.audit_dir, "audit_calidad_datos")

    df_rechazados = _construir_df_rechazados(bitacora)
    guardar_tabla_medallion(df_rechazados, cfg.audit_dir, "audit_registros_rechazados")

    rech_por_tabla: dict[str, int] = {}
    if not df_rechazados.empty:
        conteos = df_rechazados["tabla_destino"].value_counts().to_dict()
        rech_por_tabla = {str(k): int(v) for k, v in conteos.items()}

    n_scd2 = len(silver["dim_empresas_scd2"])
    reconciliacion = pd.DataFrame(
        [
            _fila_reconciliacion(
                "dim_kams",
                bronze["dim_kams"],
                silver["dim_kams"],
                "100% filas válidas conservadas; métricas movidas a "
                "audit_metricas_origen_kams; Sin asignar homologado a KAM-UNASSIGNED",
                rech_por_tabla.get("dim_kams", 0),
            ),
            _fila_reconciliacion(
                "dim_empresas",
                bronze["dim_empresas"],
                silver["dim_empresas"],
                f"100% filas válidas conservadas; métricas movidas a Gold/Auditoría; "
                f"historial en dim_empresas_scd2 ({n_scd2} filas)",
                rech_por_tabla.get("dim_empresas", 0),
            ),
            _fila_reconciliacion(
                "dim_personas",
                bronze["dim_personas"],
                silver["dim_personas"],
                "100% filas válidas conservadas; métricas movidas a "
                "audit_metricas_origen_personas",
                rech_por_tabla.get("dim_personas", 0),
            ),
            _fila_reconciliacion(
                "dim_eventos",
                bronze["dim_eventos"],
                silver["dim_eventos"],
                "100% filas válidas conservadas; métricas de origen movidas a "
                "audit_metricas_origen_eventos",
                rech_por_tabla.get("dim_eventos", 0),
            ),
            _fila_reconciliacion(
                "fact_asistencias",
                bronze["fact_asistencias"],
                silver["fact_asistencias"],
                "100% filas válidas conservadas; kam_id homologado a KAM-UNASSIGNED; "
                "15 filas sin empresa clasificadas",
                rech_por_tabla.get("fact_asistencias", 0),
            ),
            _fila_reconciliacion(
                "fact_encuestas_satisfaccion",
                bronze["fact_encuestas_satisfaccion"],
                silver["fact_encuestas_satisfaccion"],
                "100% filas válidas conservadas; sin inferencia de eventos ni NPS",
                rech_por_tabla.get("fact_encuestas_satisfaccion", 0),
            ),
            _fila_reconciliacion(
                "fact_movimientos_crm",
                bronze["fact_movimientos_crm"],
                silver["fact_movimientos_crm"],
                "100% filas válidas conservadas; creada PK id_movimiento y "
                "clasificados nulos de expiración",
                rech_por_tabla.get("fact_movimientos_crm", 0),
            ),
            _fila_reconciliacion(
                "audit_registros_duplicados",
                bronze["registros_duplicados"],
                df_audit_dup,
                "100% filas conservadas con trazabilidad y clasificación",
                0,
            ),
        ]
    )
    guardar_tabla_medallion(
        reconciliacion, cfg.audit_dir, "audit_reconciliacion_origen_destino"
    )

    df_audit_cargas = pd.DataFrame(bitacora.registros_cargas)
    guardar_tabla_medallion(df_audit_cargas, cfg.audit_dir, "audit_cargas")
    return {
        "calidad": df_audit_calidad,
        "rechazados": df_rechazados,
        "reconciliacion": reconciliacion,
        "cargas": df_audit_cargas,
    }
