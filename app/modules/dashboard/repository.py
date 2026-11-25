"""Consultas de solo lectura sobre la capa Silver para el tablero."""

from datetime import date, timedelta
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.modules.eda.models.silver_dim_empresa import SilverDimEmpresa
from app.modules.eda.models.silver_dim_evento import SilverDimEvento
from app.modules.eda.models.silver_dim_kam import SilverDimKam
from app.modules.eda.models.silver_fact_asistencia import SilverFactAsistencia
from app.modules.eda.models.silver_fact_encuesta_satisfaccion import (
    SilverFactEncuestaSatisfaccion,
)
from app.modules.eda.models.silver_fact_movimiento_crm import (
    SilverFactMovimientoCrm,
)


class DashboardSilverRepository:
    """Expone agregaciones del dashboard sin depender de tablas Gold."""

    def __init__(self, session: Session) -> None:
        """Inicializa el repositorio con una sesión inyectada por FastAPI."""
        self.session = session

    def obtener_filtros(self) -> dict[str, list[str]]:
        """Obtiene los valores disponibles para filtros del tablero."""
        def values(column: Any) -> list[str]:
            return [
                str(row[0])
                for row in self.session.query(column)
                .filter(column.isnot(None), column != "")
                .distinct()
                .order_by(column)
                .all()
            ]

        return {
            "kams": values(SilverDimEmpresa.kam_id),
            "niveles_membresia": values(SilverDimEmpresa.nivel_membresia),
            "sectores": values(SilverDimEmpresa.sector_economico),
            "tamanos_empresa": values(SilverDimEmpresa.tamano_empresa),
            "estados_membresia": values(SilverDimEmpresa.estado_membresia_detalle),
            "ciudades": values(SilverDimEmpresa.ciudad),
            "lineas_oferta": values(SilverDimEvento.linea_oferta_2027),
            "modalidades_evento": values(SilverDimEvento.modalidad),
            "periodos_asistencia": values(SilverFactAsistencia.periodo_mes_iso),
            "ciudades_evento": values(SilverFactAsistencia.ciudad_evento),
        }

    def obtener_resumen(self, fecha_referencia: date) -> dict[str, Any]:
        """Calcula KPIs de afiliación, vencimientos y participación Silver."""
        reference = fecha_referencia.isoformat()
        total_empresas = self.session.query(SilverDimEmpresa).count()
        afiliados_activos = (
            self.session.query(SilverDimEmpresa)
            .filter(SilverDimEmpresa.es_membresia_activa.is_(True))
            .count()
        )
        vencimientos: dict[str, int] = {}
        for days in (30, 60, 90):
            end = (fecha_referencia + timedelta(days=days)).isoformat()
            vencimientos[str(days)] = (
                self.session.query(SilverDimEmpresa)
                .filter(
                    SilverDimEmpresa.es_membresia_activa.is_(True),
                    SilverDimEmpresa.fecha_expiracion >= reference,
                    SilverDimEmpresa.fecha_expiracion <= end,
                )
                .count()
            )

        empresas_con_servicio = (
            self.session.query(
                func.count(func.distinct(SilverFactAsistencia.id_empresa))
            )
            .filter(SilverFactAsistencia.id_empresa.isnot(None))
            .scalar()
            or 0
        )
        total_asistencias = self.session.query(SilverFactAsistencia).count()
        total_respuestas = self.session.query(SilverFactEncuestaSatisfaccion).count()
        satisfaccion = (
            self.session.query(
                func.avg(SilverFactEncuestaSatisfaccion.promedio_satisfaccion)
            ).scalar()
            or 0.0
        )
        return {
            "fecha_referencia": reference,
            "total_empresas": int(total_empresas),
            "afiliados_activos": int(afiliados_activos),
            "vencimientos_proximos": vencimientos,
            "empresas_con_servicio": int(empresas_con_servicio),
            "porcentaje_afiliados_en_servicios": round(
                (int(empresas_con_servicio) / afiliados_activos) * 100
                if afiliados_activos
                else 0.0,
                2,
            ),
            "total_asistencias": int(total_asistencias),
            "total_respuestas_satisfaccion": int(total_respuestas),
            "promedio_satisfaccion_1_5": round(float(satisfaccion), 2),
            "capa_datos": "silver",
        }

    def listar_afiliados(
        self,
        *,
        kam_id: str | None,
        nivel_membresia: str | None,
        sector: str | None,
        tamano_empresa: str | None,
        estado_membresia: str | None,
        ciudad: str | None,
        solo_activos: bool,
        offset: int,
        limit: int,
    ) -> dict[str, Any]:
        """Lista empresas con información útil para la cartera comercial."""
        query = self.session.query(SilverDimEmpresa, SilverDimKam).outerjoin(
            SilverDimKam, SilverDimKam.kam_id == SilverDimEmpresa.kam_id
        )
        if kam_id:
            query = query.filter(SilverDimEmpresa.kam_id == kam_id)
        if nivel_membresia:
            query = query.filter(SilverDimEmpresa.nivel_membresia == nivel_membresia)
        if sector:
            query = query.filter(SilverDimEmpresa.sector_economico == sector)
        if tamano_empresa:
            query = query.filter(SilverDimEmpresa.tamano_empresa == tamano_empresa)
        if estado_membresia:
            query = query.filter(
                SilverDimEmpresa.estado_membresia_detalle == estado_membresia
            )
        if ciudad:
            query = query.filter(SilverDimEmpresa.ciudad == ciudad)
        if solo_activos:
            query = query.filter(SilverDimEmpresa.es_membresia_activa.is_(True))

        total = query.count()
        rows = (
            query.order_by(SilverDimEmpresa.fecha_expiracion, SilverDimEmpresa.id_empresa)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": [
                {
                    "id_empresa": empresa.id_empresa,
                    "kam_id": empresa.kam_id,
                    "kam_nombre": kam.responsable_nombre if kam else None,
                    "membresia_activa": empresa.es_membresia_activa,
                    "nivel_membresia": empresa.nivel_membresia,
                    "sector_economico": empresa.sector_economico,
                    "tamano_empresa": empresa.tamano_empresa,
                    "estado_membresia": empresa.estado_membresia_detalle,
                    "ciudad": empresa.ciudad,
                    "fecha_afiliacion": empresa.fecha_afiliacion,
                    "fecha_miembro_desde": empresa.fecha_miembro_desde,
                    "fecha_expiracion": empresa.fecha_expiracion,
                }
                for empresa, kam in rows
            ],
        }

    def obtener_participacion(
        self,
        *,
        fecha_desde: str | None,
        fecha_hasta: str | None,
        kam_id: str | None,
        ciudad_evento: str | None,
    ) -> list[dict[str, Any]]:
        """Agrupa participación por evento, línea y modalidad."""
        query = self.session.query(
            SilverDimEvento.id_evento.label("id_evento"),
            SilverDimEvento.nombre_evento.label("nombre_evento"),
            SilverDimEvento.linea_oferta_2027.label("linea_oferta"),
            SilverDimEvento.modalidad.label("modalidad"),
            SilverDimEvento.fecha_evento.label("fecha_evento"),
            func.count(SilverFactAsistencia.id_asistencia).label("asistencias"),
            func.count(func.distinct(SilverFactAsistencia.id_empresa)).label(
                "empresas_distintas"
            ),
            func.count(func.distinct(SilverFactAsistencia.id_persona)).label(
                "personas_distintas"
            ),
        ).join(
            SilverFactAsistencia,
            SilverFactAsistencia.id_evento == SilverDimEvento.id_evento,
        )
        if fecha_desde:
            query = query.filter(SilverFactAsistencia.fecha_evento >= fecha_desde)
        if fecha_hasta:
            query = query.filter(SilverFactAsistencia.fecha_evento <= fecha_hasta)
        if kam_id:
            query = query.filter(SilverFactAsistencia.kam_id == kam_id)
        if ciudad_evento:
            query = query.filter(SilverFactAsistencia.ciudad_evento == ciudad_evento)
        rows = (
            query.group_by(
                SilverDimEvento.id_evento,
                SilverDimEvento.nombre_evento,
                SilverDimEvento.linea_oferta_2027,
                SilverDimEvento.modalidad,
                SilverDimEvento.fecha_evento,
            )
            .order_by(SilverDimEvento.fecha_evento.desc())
            .all()
        )
        return [dict(row._mapping) for row in rows]

    def obtener_satisfaccion(
        self, *, fecha_desde: str | None, fecha_hasta: str | None
    ) -> list[dict[str, Any]]:
        """Calcula satisfacción y NPS desde encuestas Silver por evento."""
        promotores = func.sum(
            case(
                (
                    SilverFactEncuestaSatisfaccion.categoria_nps_adaptado_1_5
                    == "PROMOTOR",
                    1,
                ),
                else_=0,
            )
        )
        detractores = func.sum(
            case(
                (
                    SilverFactEncuestaSatisfaccion.categoria_nps_adaptado_1_5
                    == "DETRACTOR",
                    1,
                ),
                else_=0,
            )
        )
        total = func.count(SilverFactEncuestaSatisfaccion.id_respuesta)
        query = self.session.query(
            SilverFactEncuestaSatisfaccion.id_evento.label("id_evento"),
            SilverDimEvento.nombre_evento.label("nombre_evento"),
            SilverFactEncuestaSatisfaccion.periodo_mes_iso.label("periodo_mes"),
            total.label("respuestas"),
            func.avg(SilverFactEncuestaSatisfaccion.promedio_satisfaccion).label(
                "promedio_satisfaccion"
            ),
            promotores.label("promotores"),
            detractores.label("detractores"),
        ).outerjoin(
            SilverDimEvento,
            SilverDimEvento.id_evento == SilverFactEncuestaSatisfaccion.id_evento,
        )
        if fecha_desde:
            query = query.filter(
                SilverFactEncuestaSatisfaccion.fecha_encuesta >= fecha_desde
            )
        if fecha_hasta:
            query = query.filter(
                SilverFactEncuestaSatisfaccion.fecha_encuesta <= fecha_hasta
            )
        rows = query.group_by(
            SilverFactEncuestaSatisfaccion.id_evento,
            SilverDimEvento.nombre_evento,
            SilverFactEncuestaSatisfaccion.periodo_mes_iso,
        ).order_by(SilverFactEncuestaSatisfaccion.periodo_mes_iso.desc()).all()
        response: list[dict[str, Any]] = []
        for row in rows:
            data = dict(row._mapping)
            replies = int(data["respuestas"] or 0)
            data["promedio_satisfaccion"] = round(
                float(data["promedio_satisfaccion"] or 0), 2
            )
            data["nps_adaptado_1_5"] = round(
                (
                    (int(data["promotores"] or 0) - int(data["detractores"] or 0))
                    / replies
                    * 100
                )
                if replies
                else 0.0,
                2,
            )
            response.append(data)
        return response

    def obtener_renovaciones(
        self,
        *,
        periodo_desde: str | None,
        periodo_hasta: str | None,
        kam_id: str | None,
    ) -> list[dict[str, Any]]:
        """Agrupa renovaciones y cierres facturados por mes y ejecutiva."""
        query = self.session.query(
            SilverFactMovimientoCrm.periodo_mes_iso.label("periodo_mes"),
            SilverFactMovimientoCrm.kam_id.label("kam_id"),
            func.count(SilverFactMovimientoCrm.id_movimiento).label("movimientos"),
            func.sum(
                case((SilverFactMovimientoCrm.es_renovacion.is_(True), 1), else_=0)
            ).label("renovaciones"),
            func.sum(
                case(
                    (SilverFactMovimientoCrm.es_cierre_facturado.is_(True), 1),
                    else_=0,
                )
            ).label("cierres_facturados"),
        )
        if periodo_desde:
            query = query.filter(
                SilverFactMovimientoCrm.periodo_mes_iso >= periodo_desde
            )
        if periodo_hasta:
            query = query.filter(
                SilverFactMovimientoCrm.periodo_mes_iso <= periodo_hasta
            )
        if kam_id:
            query = query.filter(SilverFactMovimientoCrm.kam_id == kam_id)
        rows = (
            query.group_by(
                SilverFactMovimientoCrm.periodo_mes_iso,
                SilverFactMovimientoCrm.kam_id,
            )
            .order_by(
                SilverFactMovimientoCrm.periodo_mes_iso.desc(),
                SilverFactMovimientoCrm.kam_id,
            )
            .all()
        )
        return [
            {
                **dict(row._mapping),
                "movimientos": int(row.movimientos or 0),
                "renovaciones": int(row.renovaciones or 0),
                "cierres_facturados": int(row.cierres_facturados or 0),
            }
            for row in rows
        ]

    def obtener_segmentos(self, fecha_referencia: date, limit: int) -> dict[str, Any]:
        """Devuelve listas accionables de comunicación disponibles en Silver."""
        cutoff = (fecha_referencia + timedelta(days=90)).isoformat()
        reference = fecha_referencia.isoformat()
        participes = self.session.query(SilverFactAsistencia.id_empresa).filter(
            SilverFactAsistencia.id_empresa.isnot(None)
        )
        vencimientos = (
            self.session.query(SilverDimEmpresa)
            .filter(
                SilverDimEmpresa.es_membresia_activa.is_(True),
                SilverDimEmpresa.fecha_expiracion >= reference,
                SilverDimEmpresa.fecha_expiracion <= cutoff,
            )
            .order_by(SilverDimEmpresa.fecha_expiracion)
            .limit(limit)
            .all()
        )
        sin_participacion = (
            self.session.query(SilverDimEmpresa)
            .filter(
                SilverDimEmpresa.es_membresia_activa.is_(True),
                ~SilverDimEmpresa.id_empresa.in_(participes),
            )
            .order_by(SilverDimEmpresa.id_empresa)
            .limit(limit)
            .all()
        )
        no_afiliados = (
            self.session.query(SilverFactAsistencia)
            .filter(SilverFactAsistencia.es_afiliado.is_(False))
            .limit(limit)
            .all()
        )
        return {
            "fecha_referencia": reference,
            "vencimientos_proximos": [
                {
                    "id_empresa": row.id_empresa,
                    "kam_id": row.kam_id,
                    "fecha_expiracion": row.fecha_expiracion,
                }
                for row in vencimientos
            ],
            "afiliados_sin_participacion": [
                {"id_empresa": row.id_empresa, "kam_id": row.kam_id}
                for row in sin_participacion
            ],
            "asistentes_no_afiliados": [
                {
                    "id_asistencia": row.id_asistencia,
                    "id_persona": row.id_persona,
                    "id_empresa": row.id_empresa,
                    "id_evento": row.id_evento,
                }
                for row in no_afiliados
            ],
        }
