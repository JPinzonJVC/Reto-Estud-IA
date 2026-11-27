# Recomendador de eventos y propensión de asistencia

## Estado

La recomendación de línea por afinidad histórica es posible con los registros observados;
la probabilidad supervisada de asistencia está bloqueada por falta de negativos de
convocatoria verificables.

## Datos y límites

- 34 eventos con fechas, línea y modalidad; distribución de líneas: Anticipar 19, Pares
  6, Foro 6 y Evento grande 3.
- 3.401 registros de asistencia enlazados a 33 eventos y 1.197 empresas.
- 725 encuestas, pero ninguna enlazada a un evento en Gold; 142 no tienen empresa.
- No existe tabla de empresas invitadas/convocadas que no asistieron.

La asistencia observada puede servir como positivo histórico. No se etiqueta como cero a
una empresa sin asistencia porque no hay constancia de que hubiera recibido invitación.
Los 34 eventos y cuatro líneas tampoco bastan para inferir automáticamente una
preferencia 2027 generalizable.

## Baseline descriptivo implementado

`recommend_historical_line` selecciona la línea con más eventos distintos observados por
empresa, deduplicando asistentes de un mismo evento. Sobre la base actual produjo
recomendación histórica para 1.197 empresas: Anticipar 1.013, Evento grande 144, Foro 21
y Pares 19. No se calcula probabilidad de asistencia y no se persiste el resultado.

La distribución refleja tanto afinidad como disponibilidad desigual de eventos: hay 19
eventos Anticipar y solo 3 Evento grande. El baseline sirve como referencia de afinidad,
no como recomendación 2027 aprobada ni comparación estadística entre líneas.

## Siguiente paso

Incorporar evidencia de convocatoria con claves empresa-evento y fechas de invitación,
respetando autorización de tratamiento. Después se podrá construir una fila empresa-evento
al corte previo a la invitación y evaluar Precision@K, Recall@K, MAP@K, PR-AUC y Brier.
Hasta entonces, mostrar afinidad como frecuencia histórica descriptiva, separada de la
probabilidad de asistencia.
