import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { mlApi } from '../api/ml';
import type { MlCase, MlOverview, MlResult, MlResultPage } from '../types';

const PAGE_SIZE = 12;
const CASES: Array<{ id: MlCase; title: string; kind: string; description: string }> = [
  { id: 'fidelidad_rfm_s', title: 'Fidelización', kind: 'No supervisado · RFM-S', description: 'Segmentos descriptivos de empresas con satisfacción observada.' },
  { id: 'recomendacion_linea', title: 'Recomendaciones', kind: 'Afinidad histórica', description: 'Línea con mayor afinidad en el historial de eventos de cada empresa.' },
  { id: 'churn_heuristico', title: 'Riesgo de churn', kind: 'Score heurístico', description: 'Puntos y semáforo calculados por reglas de negocio en Gold.' },
  { id: 'lead_prioridad', title: 'Lead scoring', kind: 'Prioridad descriptiva', description: 'Orden de seguimiento basado en interacciones positivas observadas.' },
];

type Summary = Partial<Record<MlCase, MlResultPage>>;

export function MlDashboard() {
  const [activeCase, setActiveCase] = useState<MlCase>('fidelidad_rfm_s');
  const [summary, setSummary] = useState<Summary>({});
  const [overview, setOverview] = useState<MlOverview | null>(null);
  const [page, setPage] = useState<MlResultPage | null>(null);
  const [companyDraft, setCompanyDraft] = useState('');
  const [company, setCompany] = useState('');
  const [segmentDraft, setSegmentDraft] = useState('');
  const [segment, setSegment] = useState('');
  const [offset, setOffset] = useState(0);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingPage, setLoadingPage] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refreshSummary = useCallback(async () => {
    setLoadingSummary(true);
    try {
      const [result, fidelity] = await Promise.all([
        mlApi.overview(),
        mlApi.results('fidelidad_rfm_s', { limit: 200 }),
      ]);
      setOverview(result);
      setSummary({ fidelidad_rfm_s: fidelity });
      setError(null);
      setLastUpdated(new Date());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo consultar Machine Learning.');
    } finally {
      setLoadingSummary(false);
    }
  }, []);

  const refreshPage = useCallback(async () => {
    setLoadingPage(true);
    try {
      const result = await mlApi.results(activeCase, {
        limit: PAGE_SIZE,
        offset,
        company,
        segment,
      });
      setPage(result);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No se pudo consultar el caso de uso.');
    } finally {
      setLoadingPage(false);
    }
  }, [activeCase, company, offset, segment]);

  useEffect(() => {
    void refreshSummary();
  }, [refreshSummary]);

  useEffect(() => {
    const activate = () => {
      void refreshSummary();
      void refreshPage();
    };
    window.addEventListener('ml:activate', activate);
    return () => window.removeEventListener('ml:activate', activate);
  }, [refreshPage, refreshSummary]);

  useEffect(() => {
    void refreshPage();
  }, [refreshPage]);

  const current = CASES.find(({ id }) => id === activeCase)!;
  const caseStatus = (id: MlCase) => overview?.casos_uso.find((item) => item.caso_uso === id);
  const fidelityRows = summary.fidelidad_rfm_s?.items ?? [];
  const clusterProfile = useMemo(() => buildClusterProfile(fidelityRows), [fidelityRows]);
  const availableTotal = overview?.resultados_totales ?? 0;
  const lastCutoff = overview?.fecha_corte ?? null;

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCompany(companyDraft.trim());
    setSegment(segmentDraft.trim());
    setOffset(0);
  }

  function selectCase(id: MlCase) {
    setActiveCase(id);
    setOffset(0);
    setSegmentDraft('');
    setSegment('');
  }

  const visiblePage = page?.caso_uso === activeCase ? page : null;
  const start = (visiblePage?.total ?? 0) === 0 ? 0 : offset + 1;
  const end = Math.min(offset + PAGE_SIZE, visiblePage?.total ?? 0);

  return (
    <div className="ml-shell">
      <header className="ml-header">
        <div>
          <p className="ml-eyebrow">ACTHO 360 · ANALÍTICA RESPONSABLE</p>
          <h1>Machine Learning</h1>
          <p className="ml-muted">Resultados descriptivos y heurísticos conectados con Gold. Ningún score de afinidad se interpreta como probabilidad.</p>
        </div>
        <button className="ml-button ml-button--primary" onClick={() => { void refreshSummary(); void refreshPage(); }} disabled={loadingSummary || loadingPage}>
          {loadingSummary || loadingPage ? 'Actualizando…' : 'Actualizar datos'}
        </button>
      </header>

      <section className="ml-overview" aria-label="Resumen de Machine Learning">
        <SummaryCard label="Resultados disponibles" value={loadingSummary ? '…' : formatNumber(availableTotal)} detail="En el corte vigente" icon="Σ" />
        <SummaryCard label="Último corte" value={lastCutoff ?? 'Sin datos'} detail={lastUpdated ? `Consultado ${formatDateTime(lastUpdated)}` : 'Fecha registrada por resultado'} icon="◷" />
        <SummaryCard label="Métodos activos" value={String(overview?.casos_uso.filter((item) => item.resultados_disponibles > 0).length ?? 0)} detail="De 4 casos de uso" icon="◈" />
        <SummaryCard label="Modelos aprobados disponibles" value={String(overview?.modelos_aprobados_disponibles ?? 0)} detail="Artefactos con manifiesto aprobado" icon="◎" />
      </section>

      <section className="ml-case-grid" aria-label="Casos de uso">
        {CASES.map((item, index) => (
          <button
            className={`ml-case-card${activeCase === item.id ? ' is-active' : ''}`}
            key={item.id}
            onClick={() => selectCase(item.id)}
            aria-pressed={activeCase === item.id}
          >
            <span className="ml-case-index">0{index + 1}</span>
            <span className="ml-case-title">{item.title}</span>
            <span className="ml-case-kind">{item.kind}</span>
            <strong>{loadingSummary ? '…' : formatNumber(caseStatus(item.id)?.resultados_disponibles ?? 0)}</strong>
            <span className="ml-case-status">{caseStatus(item.id)?.estado ?? 'SIN_RESULTADOS'} · {item.kind}</span>
            <span className="ml-case-caption">{item.description}</span>
          </button>
        ))}
      </section>

      {error && <div className="ml-alert" role="alert">{error}</div>}
      {!error && availableTotal === 0 && !loadingSummary && (
        <div className="ml-alert ml-alert--info" role="status">
          Todavía no hay resultados persistidos. Tras validar la migración, ejecuta el proceso descriptivo para poblar Gold.
        </div>
      )}

      <section className="ml-workspace" aria-labelledby="ml-active-title">
        <div className="ml-workspace-heading">
          <div>
            <p className="ml-eyebrow">{current.kind}</p>
            <h2 id="ml-active-title">{current.title}</h2>
            <p className="ml-muted">{current.description}</p>
          </div>
          {(caseStatus(activeCase)?.version || caseStatus(activeCase)?.fecha_corte) && <span className="ml-version">{caseStatus(activeCase)?.version ?? 'Sin versión'} · corte {formatDate(caseStatus(activeCase)?.fecha_corte ?? null)}</span>}
        </div>

        {activeCase === 'churn_heuristico' && (
          <div className="ml-alert ml-alert--info" role="note">
            Modelo predictivo de Churn no disponible: etiquetas insuficientes para entrenamiento validado. Los datos de esta vista son un score heurístico, no una probabilidad.
          </div>
        )}
        {activeCase === 'lead_prioridad' && (
          <div className="ml-alert ml-alert--info" role="note">
            Esta lista prioriza interacción histórica observada. No estima probabilidad de conversión ni considera la ausencia de cierre como resultado negativo.
          </div>
        )}

        {activeCase === 'fidelidad_rfm_s' && <FidelityProfile rows={fidelityRows} clusters={clusterProfile} />}

        <form className="ml-filters" onSubmit={applyFilters}>
          <label>
            Buscar empresa
            <input value={companyDraft} onChange={(event) => setCompanyDraft(event.target.value)} placeholder="ID de empresa" />
          </label>
          <label>
            {activeCase === 'recomendacion_linea' ? 'Línea recomendada' : activeCase === 'churn_heuristico' || activeCase === 'fidelidad_rfm_s' ? 'Segmento / semáforo' : 'Criterio'}
            <input value={segmentDraft} onChange={(event) => setSegmentDraft(event.target.value)} placeholder="Filtro exacto (opcional)" />
          </label>
          <button className="ml-button ml-button--primary" type="submit">Aplicar filtros</button>
          <button className="ml-button" type="button" onClick={() => { setCompanyDraft(''); setCompany(''); setSegmentDraft(''); setSegment(''); setOffset(0); }}>Limpiar</button>
        </form>

        {loadingPage ? (
          <p className="ml-empty" role="status">Cargando resultados…</p>
        ) : visiblePage && visiblePage.items.length > 0 ? (
          <ResultsTable caso={activeCase} rows={visiblePage.items} />
        ) : (
          <p className="ml-empty">No hay resultados para este corte y estos filtros.</p>
        )}

        <footer className="ml-pagination">
          <span>{formatNumber(start)}–{formatNumber(end)} de {formatNumber(visiblePage?.total ?? 0)}</span>
          <div>
            <button className="ml-button" disabled={offset === 0 || loadingPage} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Anterior</button>
            <button className="ml-button" disabled={!visiblePage || offset + PAGE_SIZE >= visiblePage.total || loadingPage} onClick={() => setOffset(offset + PAGE_SIZE)}>Siguiente</button>
          </div>
        </footer>
      </section>
    </div>
  );
}

function SummaryCard({ label, value, detail, icon }: { label: string; value: string; detail: string; icon: string }) {
  return <article className="ml-summary-card"><span className="ml-summary-icon" aria-hidden="true">{icon}</span><p>{label}</p><strong>{value}</strong><small>{detail}</small></article>;
}

function FidelityProfile({ rows, clusters }: { rows: MlResult[]; clusters: Array<{ name: string; count: number; features: Record<string, number> }> }) {
  if (!rows.length) return null;
  const colors = ['#3d45c9', '#1b9f86', '#d79428', '#8a62c4', '#df6470'];
  const maxCount = Math.max(...clusters.map(({ count }) => count), 1);
  const featureNames: Record<string, string> = {
    recency: 'Recencia', frequency: 'Frecuencia', amplitude: 'Amplitud', tenure: 'Antigüedad', satisfaction: 'Satisfacción',
  };
  return (
    <div className="ml-profile-grid">
      <article className="ml-chart-card">
        <div className="ml-chart-heading"><div><p className="ml-eyebrow">COHORTE CON SATISFACCIÓN</p><h3>Distribución de segmentos</h3></div><span>{formatNumber(rows.length)} empresas</span></div>
        <div className="ml-distribution" role="img" aria-label={`Distribución de empresas en ${clusters.length} segmentos descriptivos`}>
          {clusters.map((cluster, index) => (
            <div className="ml-distribution-row" key={cluster.name}>
              <span>{cluster.name}</span><div className="ml-bar-track"><i style={{ width: `${(cluster.count / maxCount) * 100}%`, background: colors[index % colors.length] }} /></div><strong>{cluster.count}</strong>
            </div>
          ))}
        </div>
      </article>
      <article className="ml-chart-card">
        <div className="ml-chart-heading"><div><p className="ml-eyebrow">PERFIL MEDIO</p><h3>Variables por segmento</h3></div><span>Índice percentil 0–100</span></div>
        <div className="ml-feature-profiles">
          {clusters.slice(0, 4).map((cluster, index) => (
            <div className="ml-feature-cluster" key={cluster.name}>
              <strong style={{ color: colors[index % colors.length] }}>{cluster.name}</strong>
              {Object.entries(featureNames).map(([feature, label]) => {
                const value = cluster.features[feature] ?? 0;
                return <div className="ml-feature-row" key={feature}><span>{label}</span><div className="ml-bar-track"><i style={{ width: `${Math.max(0, Math.min(value, 100))}%`, background: colors[index % colors.length] }} /></div><b>{value.toFixed(0)}</b></div>;
              })}
            </div>
          ))}
        </div>
      </article>
    </div>
  );
}

function ResultsTable({ caso, rows }: { caso: MlCase; rows: MlResult[] }) {
  const columns = CASES.find(({ id }) => id === caso)!;
  const fidelity = caso === 'fidelidad_rfm_s';
  const recommendation = caso === 'recomendacion_linea';
  const churn = caso === 'churn_heuristico';
  return (
    <div className="ml-table-wrap">
      <table>
        <caption className="ml-sr-only">{columns.title}: resultados de empresas</caption>
        <thead><tr>
          <th scope="col">Empresa</th>
          {fidelity && <><th scope="col">Segmento</th><th scope="col">Índice RFM-S</th><th scope="col">Variables del perfil</th></>}
          {recommendation && <><th scope="col">Línea sugerida</th><th scope="col">Afinidad histórica</th><th scope="col">Eventos de soporte</th><th scope="col">Justificación</th></>}
          {churn && <><th scope="col">Semáforo</th><th scope="col">Puntos heurísticos</th><th scope="col">Señales</th></>}
          {caso === 'lead_prioridad' && <><th scope="col">Prioridad</th><th scope="col">Eventos observados</th><th scope="col">Criterio</th></>}
          <th scope="col">Estado</th>
        </tr></thead>
        <tbody>{rows.map((row) => (
          <tr key={`${row.id_empresa}-${row.id_ejecucion}`}>
            <th scope="row">{row.id_empresa}</th>
            {fidelity && <><td><span className="ml-tag">{row.segmento_o_linea ?? '—'}</span></td><td>{row.score === null ? '—' : row.score.toFixed(1)}</td><td>{formatFeatureList(row.justificacion)}</td></>}
            {recommendation && <><td>{row.segmento_o_linea ?? '—'}</td><td>{row.score === null ? '—' : `${row.score.toFixed(1)}%`}</td><td>{row.soporte ?? 0}</td><td>{formatSupport(row.justificacion)}</td></>}
            {churn && <><td><span className={`ml-tag ml-tag--${normalizeStatus(row.segmento_o_linea)}`}>{row.segmento_o_linea ?? 'NO_APLICA'}</span></td><td>{row.score?.toFixed(0) ?? '—'}</td><td>{formatFlags(row.justificacion)}</td></>}
            {caso === 'lead_prioridad' && <><td><span className="ml-tag ml-tag--priority">Interacción observada</span></td><td>{row.soporte ?? 0}</td><td>{formatFlags(row.justificacion)}</td></>}
            <td><span className="ml-status">{row.estado}</span></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function buildClusterProfile(rows: MlResult[]) {
  const groups = new Map<string, MlResult[]>();
  rows.forEach((row) => {
    const name = row.segmento_o_linea ?? 'SIN_SEGMENTO';
    groups.set(name, [...(groups.get(name) ?? []), row]);
  });
  return [...groups.entries()].map(([name, items]) => {
    const features = ['recency', 'frequency', 'amplitude', 'tenure', 'satisfaction'];
    return {
      name,
      count: items.length,
      features: Object.fromEntries(features.map((feature) => {
        const values = items.map((item) => Number(item.justificacion[feature])).filter(Number.isFinite);
        return [feature, values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0];
      })),
    };
  }).sort((left, right) => left.name.localeCompare(right.name));
}

function formatFeatureList(data: Record<string, unknown>) {
  const names: Record<string, string> = { recency: 'Recencia', frequency: 'Frecuencia', amplitude: 'Amplitud', tenure: 'Antigüedad', satisfaction: 'Satisfacción' };
  return Object.entries(names).map(([key, label]) => `${label} ${Number(data[key] ?? 0).toFixed(0)}`).join(' · ');
}

function formatFlags(data: Record<string, unknown>) {
  const entries = Object.entries(data).filter(([key, value]) => key !== 'criterio' && value === true);
  const criterion = typeof data.criterio === 'string' ? data.criterio : null;
  const labels = entries.map(([key]) => key.replaceAll('_', ' '));
  if (criterion) labels.push(criterion);
  return labels.length ? labels.join(' · ') : 'Interacción histórica registrada';
}

function formatSupport(data: Record<string, unknown>) {
  const count = data.eventos_distintos_linea;
  const total = data.eventos_distintos_total;
  return typeof count === 'number' && typeof total === 'number' ? `${count} de ${total} eventos distintos` : 'Historial observado';
}

function normalizeStatus(value: string | null) {
  return (value ?? 'no_aplica').toLocaleLowerCase().replaceAll('_', '-');
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('es-CO').format(value);
}

function formatDate(value: string | null) {
  if (!value) return '—';
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00`);
  return Number.isNaN(parsed.valueOf()) ? value : new Intl.DateTimeFormat('es-CO').format(parsed);
}

function formatDateTime(value: Date) {
  return new Intl.DateTimeFormat('es-CO', { hour: '2-digit', minute: '2-digit' }).format(value);
}
