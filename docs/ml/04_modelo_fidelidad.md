# Fidelity & Loyalty — RFM-S

## Estado

Implementados extracción sin PII, componentes RFM-S, comparación KMeans/GaussianMixture
y perfilado de clusters. Resultado **exploratorio, no aprobado para persistir en Gold**.

## Cohorte y features

La población elegible contiene 435 afiliados activos. 140 (32,18%) tienen satisfacción
promedio enlazada; los 295 restantes quedan fuera del índice RFM-S para no convertir una
encuesta ausente en una valoración imputada. El NPS no está disponible en ninguna fila.
El código produce score solo para las 140 empresas con S observado.

- R: días sin participación, convertido a percentil inverso; empresas sin asistencia
  observada reciben el tope de 365 días del horizonte anual.
- F: eventos únicos del periodo Gold.
- A: personas distintas más indicadores binarios de comunidades y pilares.
- T: número de ciclos de membresía.
- S: satisfacción promedio 1–5 transformada a percentil; no se usa NPS.

Cada dimensión se normaliza por percentiles en la cohorte de afiliados activos; el score
es la media de las cinco dimensiones. El score es relativo a esa cohorte y no se debe
comparar como escala absoluta entre snapshots sin versionar la transformación.

## Evaluación exploratoria

Se evaluaron k=2…6 con cinco semillas (42–46) para ambos algoritmos. Mejor candidato por
silhouette: KMeans con k=2 y 140 empresas.

| Algoritmo | k | Silhouette ↑ | Davies–Bouldin ↓ | Calinski–Harabasz ↑ | ARI entre semillas ↑ |
|---|---:|---:|---:|---:|---:|
| KMeans | 2 | 0,332 | 1,225 | 83,500 | 1,000 |
| KMeans | 4 | 0,281 | 1,222 | 65,839 | 0,930 |
| GaussianMixture | 2 | 0,262 | 1,296 | 63,551 | 1,000 |
| GaussianMixture | 4 | 0,192 | 1,230 | 39,140 | 0,769 |

Perfil con el candidato KMeans k=2 (medias de percentil 0–100):

| Cluster | Empresas | R | F | A | T | S | Interpretación provisional |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 59 | 54,26 | 51,06 | 49,47 | 50,00 | 58,93 | Uso menor, satisfacción reportada mayor |
| 1 | 81 | 79,28 | 84,89 | 84,62 | 50,00 | 44,11 | Uso más frecuente y amplio, satisfacción reportada menor |

La separación es descriptiva, no predice churn ni permanencia. No se asignan aún nombres
de arquetipo comercial: falta validación con KAM y una evaluación de estabilidad por
remuestreo temporal. La cobertura limitada de encuestas puede sesgar los perfiles.
El score RFM-S es la media de percentiles de la cohorte, de modo que el cluster 1 tiene
más frecuencia, recencia y amplitud observadas. La dimensión de ciclos no discrimina en
esta solución (mediana 50 en ambos grupos).

## Ejecución

Con `DATABASE_URL` configurado, la evaluación se ejecuta con:

```bash
python -m app.modules.eda.ml.fidelity.train
```

El comando lee Gold/Silver, imprime métricas agregadas y **no guarda artefactos ni
actualiza Gold**. `tests/test_ml_fidelity.py` usa solo datos sintéticos pequeños para
probar lógica; estos datos nunca son un entrenamiento ACTHO.
