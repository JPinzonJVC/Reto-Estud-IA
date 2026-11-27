# Integración de resultados ML con Gold

## Estado

Gold ya contiene las columnas propuestas en `gold_dim_empresa_360` y el mart de
comunicaciones usa controles de autorización. La base observada tiene 0 filas con valores
ML poblados; solo los 435 afiliados tienen el puntaje heurístico y semáforo de negocio.

## Requisitos antes de persistir

1. Registrar modelo, versión, corte, schema de features, algoritmo, tamaños y métricas.
2. Aprobar el modelo y su población elegible de forma explícita.
3. Validar llaves, rangos, valores finitos y correspondencia de cobertura antes de abrir
   transacción.
4. Actualizar columnas Gold de empresa mediante upsert idempotente y asociar el resultado
   a una ejecución/versionado auditable.
5. Persistir probabilidad empresa-evento en una tabla con clave compuesta empresa/evento;
   no sobrescribir un score global de empresa.
6. No modificar Silver y no permitir que predicciones cambien hechos transaccionales.
7. Respetar `autoriza_tratamiento_datos` y `apto_envio_comunicaciones` para usos de
   contacto; una predicción no otorga autorización.

## Persistencia implementada y consulta

La migración `0005_gold_ml_resultados` crea `gold_ml_resultados_empresa`. El comando
`python scripts/persist_ml_descriptive_results.py` registra resultados reales como
`EXPERIMENTAL`, `DESCRIPTIVO` o `HEURISTICO`, con versión, corte, método, explicaciones,
soporte, métricas y hash de dataset cuando aplica. La clave única permite repetir una
misma ejecución/corte de forma idempotente; nuevos cortes y versiones quedan separados.

Se registran RFM-S/cluster solo sobre empresas con satisfacción observada, afinidad por
línea apoyada en eventos históricos distintos, score heurístico ya calculado en Gold y
prioridad descriptiva de prospectos con interacción positiva observada. No son
probabilidades de retención, asistencia ni conversión. Las columnas de probabilidad de
Gold permanecen reservadas mientras no haya modelos aprobados.

Consulta: `GET /ml/resultados/{caso_uso}` con `id_empresa` y `limit` opcionales. Casos:
`fidelidad_rfm_s`, `recomendacion_linea`, `churn_heuristico` y `lead_prioridad`.

```powershell
python -m alembic upgrade head
python scripts/persist_ml_descriptive_results.py
```

No se llena la tabla automáticamente desde una petición HTTP o como efecto secundario ETL.

## API y paginación

- `GET /ml/resumen`: corte, totales, métodos por caso y manifiestos de modelo aprobados.
- `GET /ml/resultados/{caso_uso}`: filtros `buscar_empresa` (coincidencia parcial),
  `segmento` y `estado`, y paginación con `limit`/`offset`.
- Casos: `fidelidad_rfm_s`, `recomendacion_linea`, `churn_heuristico`, `lead_prioridad`.

El endpoint entrega estado, método/versión, corte, soporte, justificación y métricas; los
scores de afinidad y RFM-S declaran su tipo y no se convierten en probabilidades.
