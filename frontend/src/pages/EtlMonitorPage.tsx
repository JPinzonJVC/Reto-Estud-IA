import { useCallback, useEffect, useState } from 'react';
import { etlApi } from '../api/etl';
import { EtlStepList } from '../components/EtlStepList';
import { SchedulePanel } from '../components/SchedulePanel';
import { StatusBadge } from '../components/StatusBadge';
import { StepOutputPanel } from '../components/StepOutputPanel';
import type { EtlMonitorData, EtlStep } from '../types';

const AUTO_REFRESH_KEY = 'actho-etl-auto';

export function EtlMonitorPage() {
  const [data, setData] = useState<EtlMonitorData | null>(null);
  const [selectedStep, setSelectedStep] = useState<EtlStep | null>(null);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(() => localStorage.getItem(AUTO_REFRESH_KEY) === 'true');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState(false);
  const [triggering, setTriggering] = useState(false);

  const refresh = useCallback(async (runId = selectedRun) => {
    try {
      const result = await etlApi.getStatus(runId);
      setData(result);
      setError(null);
      setSelectedStep((current) => {
        if (current && result.steps.some((step) => step.step_id === current.step_id)) return current;
        return result.steps.find((step) => step.layer === 'GOLD')
          ?? result.steps.find((step) => step.layer === 'SILVER')
          ?? result.steps[0]
          ?? null;
      });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'No fue posible consultar el estado del flujo.');
    } finally {
      setLoading(false);
    }
  }, [selectedRun]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const handleActivate = () => void refresh(null);
    window.addEventListener('etl:activate', handleActivate);
    return () => window.removeEventListener('etl:activate', handleActivate);
  }, [refresh]);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = window.setInterval(() => {
      const etlView = document.querySelector('[data-view="etl"]');
      if (document.visibilityState === 'visible' && etlView?.classList.contains('is-active')) {
        void refresh();
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [autoRefresh, refresh]);

  function toggleAutoRefresh() {
    setAutoRefresh((enabled) => {
      localStorage.setItem(AUTO_REFRESH_KEY, String(!enabled));
      return !enabled;
    });
  }

  async function triggerFlow() {
    setTriggering(true);
    setActionError(false);
    setActionMessage('Enviando ejecución a Prefect…');
    try {
      const result = await etlApi.trigger();
      setActionMessage(`Ejecución aceptada · ${result.modo === 'prefect_deployment' ? 'Prefect' : 'modo local'} · ${result.flow_run_id ?? result.run_id ?? result.state ?? 'en cola'}`);
      setAutoRefresh(true);
      localStorage.setItem(AUTO_REFRESH_KEY, 'true');
      setSelectedRun(null);
      window.setTimeout(() => void refresh(null), 1000);
    } catch (reason) {
      setActionError(true);
      setActionMessage(reason instanceof Error ? reason.message : 'No fue posible iniciar el flujo.');
    } finally {
      setTriggering(false);
    }
  }

  if (loading && !data) return <div className="app-shell"><p className="empty-state">Cargando estado de Prefect…</p></div>;
  if (error && !data) return <div className="app-shell"><p className="alert alert--error" role="alert">{error}</p><button className="button button--primary" onClick={() => void refresh(null)}>Reintentar</button></div>;
  if (!data) return null;

  const { flow, timing, progress, steps, quality_summary: quality } = data;
  const status = timing.status || 'PENDING';

  return (
    <div className="app-shell">
      <header className="monitor-header">
        <div className="brand-lockup"><span className="brand-mark">A</span><span>ACTHO <b>360</b></span></div>
        <div className="connection-state">
          <span className={`connection-dot${flow.prefect_connected ? ' is-online' : ''}`} />
          {flow.prefect_connected ? 'Prefect API conectada' : `Auditoría DWH (${flow.fuente_auditoria})`}
        </div>
      </header>

      <section className="hero panel">
        <div className="hero-top">
          <div>
            <p className="eyebrow">PREFECT SERVER · {flow.schedule_label}</p>
            <h1>{flow.name}</h1>
            <p className="description">Flow run: {flow.prefect_latest_run_id ?? timing.run_id ?? 'Sin ejecuciones'} · Deployment: {flow.deployment}</p>
          </div>
          <div className="hero-actions">
            <button className="button button--primary" onClick={() => void triggerFlow()} disabled={triggering}>
              {triggering ? 'Disparando…' : 'Ejecutar ahora'}
            </button>
            <button className={`button${autoRefresh ? ' button--active' : ' button--quiet'}`} onClick={toggleAutoRefresh} aria-pressed={autoRefresh}>
              Auto-recarga: {autoRefresh ? 'ON' : 'OFF'}
            </button>
            <button className="button button--quiet" onClick={() => void refresh(null)}>Actualizar estado</button>
          </div>
        </div>
        {actionMessage && <p className={`action-message${actionError ? ' is-error' : ''}`} role="status">{actionMessage}</p>}
        {error && <p className="alert alert--error" role="alert">{error}</p>}
        <div className="status-line">
          <div className="status-copy"><StatusBadge status={status} /><span>{statusDescription(data)}</span></div>
          <div className="progress-number"><strong>{progress.percent}%</strong><span>PROGRESO DWH</span></div>
        </div>
        <div className="progress-track" role="progressbar" aria-valuenow={progress.percent} aria-valuemin={0} aria-valuemax={100} aria-label="Progreso DWH">
          <span className={`progress-fill${status === 'RUNNING' ? ' is-running' : ''}${status === 'FAILED' ? ' is-failed' : ''}`} style={{ width: `${progress.percent}%` }} />
        </div>
        <div className="metrics-grid">
          <Metric label="Última ejecución" value={timing.last_run_ago} detail={timing.last_run_end ?? '—'} />
          <Metric label="Próxima ejecución" value={status === 'RUNNING' ? 'Esperando fin…' : timing.next_run_in} detail={timing.next_run_iso ?? '—'} />
          <Metric label="Etapas completadas" value={`${progress.completed_steps} / ${progress.total_steps}`} detail="Silver 3NF + Gold" />
          <Metric label="Registros cargados" value={progress.registros_cargados.toLocaleString('es-CO')} detail={`${progress.registros_rechazados.toLocaleString('es-CO')} rechazados`} />
          <Metric label="Fuentes verificadas" value={`${quality.fuentes_bronze_verificadas} SHA-256`} detail={`${quality.reglas_calidad} reglas de calidad`} />
        </div>
      </section>

      <div className="content-grid">
        <EtlStepList steps={steps} selectedId={selectedStep?.step_id ?? null} onSelect={setSelectedStep} />
        <aside className="right-column">
          <StepOutputPanel step={selectedStep} />
          <SchedulePanel
            data={data}
            onSelectRun={(runId) => { setSelectedRun(runId); void refresh(runId); }}
            onScheduleSaved={() => void refresh(null)}
          />
        </aside>
      </div>
      <footer className="page-footer">ACTHO 360 · Monitor de orquestación ETL</footer>
    </div>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>;
}

function statusDescription(data: EtlMonitorData) {
  if (data.flow.prefect_latest_state === 'RUNNING') return `Ejecutando ${data.flow.prefect_latest_run_name ?? 'flujo'} en Prefect.`;
  if (data.flow.prefect_latest_message) return data.flow.prefect_latest_message;
  if (data.flow.prefect_skipped_no_changes) return 'Última revisión sin cambios en las fuentes.';
  return data.timing.last_run_start ? `Carga DWH iniciada ${data.timing.last_run_start}.` : 'Aún no hay ejecuciones registradas.';
}
