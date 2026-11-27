"""Pruebas de integración para los endpoints del pipeline ETL Medallion."""

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.eda.config import ConfiguracionETL
from app.modules.eda.router import etl_service


def _crear_config_temporal(tmp_path: Path, crear_origen: bool = True) -> ConfiguracionETL:
    """Construye una ConfiguracionETL aislada en tmp_path para pruebas."""
    origen_norm = tmp_path / "normalizados"
    if crear_origen:
        origen_norm.mkdir(parents=True, exist_ok=True)
    return ConfiguracionETL(
        origen_normalizados_dir=origen_norm,
        origen_duplicados_dir=origen_norm / "duplicados",
        salida_root_dir=tmp_path,
        parametros_temporales={"fecha_corte": "2026-11-13"},
    )


@pytest.fixture(autouse=True)
def limpiar_estado_etl_service() -> None:
    """Reinicia el estado en memoria de etl_service entre pruebas."""
    etl_service._runs.clear()
    if etl_service._lock.locked():
        etl_service._lock.release()


def test_post_etl_run_y_consulta_exitosa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ejecuta POST /etl/run y verifica el resumen en GET /etl/runs/{run_id}."""
    cfg_tmp = _crear_config_temporal(tmp_path)
    monkeypatch.setattr(
        "app.modules.eda.service.cargar_configuracion", lambda: cfg_tmp
    )

    def fake_pipeline(
        cfg: ConfiguracionETL,
        persistir_en_db: bool = False,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        assert cfg.fecha_corte == "2026-11-20"
        assert persistir_en_db is False
        return {
            "ejecucion": pd.DataFrame(
                [
                    {
                        "id_ejecucion": run_id,
                        "fecha_inicio": "2026-11-21 12:00:00",
                        "fecha_finalizacion": "2026-11-21 12:00:05",
                        "archivos_procesados": 6,
                        "registros_leidos": 100,
                        "registros_cargados": 95,
                        "registros_rechazados": 2,
                        "duplicados_identificados": 3,
                        "errores": "NINGUNO",
                        "estado_ejecucion": "EXITOSO",
                    }
                ]
            ),
            "conteos_db": {},
        }

    monkeypatch.setattr(
        "app.modules.eda.service.ejecutar_pipeline_completo", fake_pipeline
    )

    client = TestClient(app)
    resp = client.post(
        "/etl/run",
        json={"persistir_en_db": False, "fecha_corte": "2026-11-20"},
    )
    assert resp.status_code == 202
    data = resp.json()
    run_id = data["run_id"]
    assert data["estado_ejecucion"] == "EN_PROGRESO"

    detalle = client.get(f"/etl/runs/{run_id}")
    assert detalle.status_code == 200
    body = detalle.json()
    assert body["estado_ejecucion"] == "EXITOSO"
    assert body["archivos_procesados"] == 6
    assert body["registros_cargados"] == 95

    listado = client.get("/etl/runs")
    assert listado.status_code == 200
    assert any(item["id_ejecucion"] == run_id for item in listado.json())


def test_post_etl_run_fecha_invalida_retorna_422() -> None:
    """Valida que una fecha_corte mal formada sea rechazada con 422."""
    client = TestClient(app)
    resp = client.post("/etl/run", json={"fecha_corte": "21-11-2026"})
    assert resp.status_code == 422


def test_post_etl_run_conflicto_si_ya_esta_corriendo() -> None:
    """Retorna 409 Conflict si ya existe una ejecución ETL en progreso."""
    etl_service._lock.acquire()
    try:
        client = TestClient(app)
        resp = client.post("/etl/run")
        assert resp.status_code == 409
    finally:
        if etl_service._lock.locked():
            etl_service._lock.release()


def test_post_etl_run_sin_directorio_fuentes_retorna_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retorna 400 Bad Request si no existe el directorio de fuentes normalizadas."""
    cfg_tmp = _crear_config_temporal(tmp_path, crear_origen=False)
    monkeypatch.setattr(
        "app.modules.eda.service.cargar_configuracion", lambda: cfg_tmp
    )
    client = TestClient(app)
    resp = client.post("/etl/run")
    assert resp.status_code == 400


def test_get_etl_run_inexistente_retorna_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retorna 404 Not Found al consultar un run_id inexistente."""
    cfg_tmp = _crear_config_temporal(tmp_path)
    monkeypatch.setattr(
        "app.modules.eda.service.cargar_configuracion", lambda: cfg_tmp
    )
    client = TestClient(app)
    resp = client.get("/etl/runs/ETL-NO-EXISTE")
    assert resp.status_code == 404
