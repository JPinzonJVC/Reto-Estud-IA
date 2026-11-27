"""Pruebas de integración para los endpoints del Dashboard DWH y rutas ML reservadas."""

from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import get_db
from app.main import app
from app.modules.eda import cargar_configuracion, ejecutar_pipeline_completo
from migrations.versions import rev_0004_dwh_silver_3nf_gold_star as mig_0004
from tests.test_modelo_dimensional import crear_fuentes_sinteticas


@pytest.fixture(name="cliente_dwh_sqlite", scope="module")
def fixture_cliente_dwh_sqlite(
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[TestClient, None, None]:
    """Crea un entorno DWH completo sobre SQLite e inyecta get_db en FastAPI."""
    base_dir: Path = tmp_path_factory.mktemp("dashboard_dwh_api")
    norm_dir = base_dir / "norm"
    dup_dir = norm_dir / "duplicados"
    out_dir = base_dir / "input"
    crear_fuentes_sinteticas(norm_dir, dup_dir)

    db_path = base_dir / "dwh_dashboard.db"
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    mig_0004.upgrade(bind=engine)

    cfg = cargar_configuracion(
        origen_normalizados_override=norm_dir,
        origen_duplicados_override=dup_dir,
        salida_root_override=out_dir,
    )
    ejecutar_pipeline_completo(cfg=cfg, persistir_en_db=True, db_engine=engine)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def _override_get_db() -> Generator[Session, None, None]:
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def test_dashboard_overview_filtros_y_evolucion(
    cliente_dwh_sqlite: TestClient,
) -> None:
    """Verifica resumen ejecutivo, semáforo, filtros y evolución de membresías."""
    r_ov = cliente_dwh_sqlite.get("/dashboard/overview?fecha_referencia=2026-11-13")
    assert r_ov.status_code == 200
    ov = r_ov.json()
    assert ov["fuente_datos"] == "postgresql"
    assert ov["afiliados_activos"] == 2
    assert set(ov["semaforo_riesgo"].keys()) == {"ROJO", "AMARILLO", "VERDE"}
    assert ov["total_asistencias"] == 4

    r_flt = cliente_dwh_sqlite.get("/dashboard/filters")
    assert r_flt.status_code == 200
    flt = r_flt.json()
    assert "subsectores" in flt
    assert "rangos_empleados" in flt

    r_evo = cliente_dwh_sqlite.get("/dashboard/membership-evolution")
    assert r_evo.status_code == 200
    evo = r_evo.json()
    assert len(evo["serie_mensual"]) >= 1
    assert "altas_totales" in evo["resumen"]


def test_kpis_segmentos_eventos_satisfaccion_y_export_csv(
    cliente_dwh_sqlite: TestClient,
) -> None:
    """Verifica KPIs empresariales, eventos, temas NLP y exportación CSV."""
    for dim in ("sector_economico", "subsector_economico", "tamano_empresa", "empleados"):
        resp = cliente_dwh_sqlite.get(f"/dashboard/segment-kpis?dimension={dim}")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1

    r_ev = cliente_dwh_sqlite.get("/dashboard/event-kpis")
    assert r_ev.status_code == 200
    ev = r_ev.json()
    assert len(ev["por_linea_2027"]) >= 1
    assert sum(x["total_asistencias"] for x in ev["eventos"]) == 4

    r_sat = cliente_dwh_sqlite.get("/dashboard/satisfaction-topics")
    assert r_sat.status_code == 200
    sat = r_sat.json()
    assert len(sat["temas_nlp"]) >= 2
    assert sat["resumen_escalas"]["estado_nps_0_10"] == "PENDIENTE_CAPTURA_0_10"

    r_seg = cliente_dwh_sqlite.get("/dashboard/communication-segments?solo_aptos=true")
    assert r_seg.status_code == 200
    assert len(r_seg.json()["resumen_segmentos"]) >= 1

    r_csv = cliente_dwh_sqlite.get("/dashboard/export/vencimientos_90d")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers["content-type"]


def test_compatibilidad_rutas_silver_y_espacio_ml_reservado(
    cliente_dwh_sqlite: TestClient,
) -> None:
    """Verifica endpoints heredados /silver/* y las 5 rutas reservadas /ml/*."""
    rutas_silver = (
        "/affiliates/silver/filters",
        "/affiliates/silver/portfolio",
        "/affiliates/silver/renewals",
        "/affiliates/silver/pillars",
        "/affiliates/silver/kam-summary",
        "/affiliates/silver/distribution",
        "/analytics/silver/filters",
        "/analytics/silver/participation",
        "/analytics/silver/audience",
        "/analytics/silver/satisfaction",
        "/analytics/silver/satisfaction-dimensions",
        "/retention/silver/segments",
        "/retention/silver/engagement-risk",
    )
    for ruta in rutas_silver:
        r = cliente_dwh_sqlite.get(ruta)
        assert r.status_code == 200, f"Fallo en {ruta}"

    r_ml = cliente_dwh_sqlite.get("/ml/status")
    assert r_ml.status_code == 200
    ml_data = r_ml.json()
    assert len(ml_data["modelos"]) == 4
    assert all(m["estado"] == "ESPACIO_RESERVADO" for m in ml_data["modelos"])

    for subruta in (
        "/ml/fidelidad",
        "/ml/publico-eventos",
        "/ml/uso-permanencia",
        "/ml/riesgo-renovacion",
    ):
        resp_m = cliente_dwh_sqlite.get(subruta)
        assert resp_m.status_code == 200
        assert resp_m.json()["estado"] == "ESPACIO_RESERVADO"
