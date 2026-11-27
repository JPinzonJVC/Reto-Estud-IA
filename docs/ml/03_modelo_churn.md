# Modelo de churn y riesgo de renovación

## Estado

**Bloqueado para entrenamiento supervisado.** No se construyó ni calibró un clasificador
porque la base actual no aporta dos clases de renovación verificables en ciclos maduros.
El puntaje y semáforo heurístico nuevo se conserva separado y no se ha escrito en Gold.

## Score heurístico implementado

`app/modules/eda/ml/churn/scoring.py` calcula los pesos iniciales pedidos: expiración
(3/2/1), baja asistencia (3), recencia mayor a 90 días (2), satisfacción <3,75 (3), NPS
detractor ≤6 (3) y monocontacto (1). Las dos señales de inactividad comparten concepto:
se aplica el mayor peso, no la suma, y ambas causas quedan visibles en `risk_flags`.

El semáforo queda ROJO desde probabilidad ML ≥0,65 o al combinar vencimiento ≤30 días,
inactividad y baja satisfacción/NPS; AMARILLO para probabilidad ≥0,35 o señal preventiva;
VERDE sin alertas; NO_APLICA para quien no tiene membresía activa. Los umbrales son
hipótesis iniciales. El código valida el rango de probabilidad y no persiste resultados.

## Datos revisados

- 1.057 ciclos de membresía para 1.055 empresas.
- 339 ciclos sin fecha de inicio y 428 sin fecha de fin.
- 129 ciclos con fechas completas y ventana de 90 días ya madura al 2026-10-29.
- En esos 129 ciclos no aparece un ciclo siguiente dentro de 90 días ni un movimiento de
  renovación facturado dentro de ±90 días.
- Hay 14 renovaciones facturadas en los movimientos CRM, pero ninguna se enlaza con esos
  129 ciclos maduros en la ventana observada.

La ausencia de renovación observada no se utiliza como clase negativa: puede reflejar
historial truncado. El estado `Cancelado`, la actividad actual, o la inactividad no
reemplazan una no-renovación confirmada.

## Diseño para destrabarlo

La unidad prevista es empresa-ciclo. Cada fila necesita fecha de corte de features,
ventana de renovación confirmada, fecha final del ciclo y evidencia CRM del resultado.
Los ciclos sin fecha o sin seguimiento completo se censuran. Se requieren ambas clases
en train y en validación temporal antes de comparar LogisticRegression, HistGradientBoosting
y RandomForest.

El semáforo heurístico ya calculado en `gold_dim_empresa_360` permanece como regla de
negocio independiente. El score actual cubre 435 afiliados activos; no se presenta como
probabilidad ML.
