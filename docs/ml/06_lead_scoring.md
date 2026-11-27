# Lead scoring de prospectos

## Estado

Bloqueado para clasificación supervisada. El sistema tiene 796 filas de `PROSPECTO_NO_AFILIADO`,
pero los prospectos actuales no tienen sector ni tamaño empresarial en Gold. No se
encontraron negativos con seguimiento completo.

## Evidencia actual

- 24 cierres facturados que son candidatos a altas (14 de Zoho y 10 de listado).
- 14 cierres de renovación.
- 39 registros `Trato en Estado`, sin membresía y sin cierre.
- 720 prospectos con asistencia histórica y 137 con encuesta.
- Todas las 796 empresas prospecto carecen de sector y tamaño en la base actual.

Los cierres de alta pueden ser positivos candidatos, pero su universo y fecha de origen
requieren reconciliación. Los tratos abiertos no son negativos y la ausencia de cierre no
demuestra una oportunidad perdida con seguimiento suficiente.

## Siguiente paso

Definir fecha de ingreso al funnel, ventana de conversión, fuente de oportunidad y regla
de censura. Solo entonces construir etiquetas de conversión verificadas, partir por
tiempo y comparar LogisticRegression, RandomForest e HistGradientBoosting. No se generó
score 0–100 ni se pobló la columna Gold.

## Criterio de priorización descriptiva

La persistencia incluye 720 de los 796 prospectos identificados porque exige al menos un
evento distinto observado (`total_eventos_anio > 0`). Los otros 76 no tienen participación
empresarial positiva observable y se excluyen: no se convierten en negativos ni se asigna
prioridad inferida. Los 137 prospectos con encuesta no se utilizan como conversión; faltan
etiquetas de seguimiento y conciliación de los cierres CRM. La lista se ordena por eventos
históricos observados y no contiene score numérico ni probabilidad.
