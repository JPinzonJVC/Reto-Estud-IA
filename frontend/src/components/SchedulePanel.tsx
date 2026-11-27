import { useEffect, useState, type FormEvent } from 'react';
import { etlApi } from '../api/etl';
import type { EtlHistoryItem, EtlMonitorData } from '../types';

interface SchedulePanelProps {
  data: EtlMonitorData;
  onSelectRun: (runId: string) => void;
  onScheduleSaved: () => void;
}

const CRON_PRESETS = [
  ['Cada 5 minutos', '*/5 * * * *'],
  ['Cada hora', '0 * * * *'],
  ['Diario 06:00', '0 6 * * *'],
  ['Semanal Lun 06:00', '0 6 * * 1'],
];

export function SchedulePanel({ data, onSelectRun, onScheduleSaved }: SchedulePanelProps) {
  const [cron, setCron] = useState(data.flow.schedule_cron);
  const [timezone, setTimezone] = useState(data.flow.schedule_timezone);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setCron(data.flow.schedule_cron);
    setTimezone(data.flow.schedule_timezone);
  }, [data.flow.schedule_cron, data.flow.schedule_timezone]);

  async function saveSchedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setIsError(false);
    setFeedback('Guardando programación…');
    try {
      const result = await etlApi.updateSchedule(cron.trim(), timezone.trim());
      setFeedback(`Guardado: ${result.schedule_label} · Próxima: ${result.next_run_iso} (${result.next_run_in})`);
      onScheduleSaved();
    } catch (reason) {
      setIsError(true);
      setFeedback(reason instanceof Error ? reason.message : 'No fue posible guardar el cron.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel schedule-panel" aria-labelledby="schedule-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Prefect Scheduler</p>
          <h2 id="schedule-heading">Cron e historial</h2>
        </div>
        <span className="subtle-count">{data.flow.schedule_label}</span>
      </div>
      <form className="schedule-form" onSubmit={saveSchedule}>
        <label>
          <span>Expresión cron</span>
          <input value={cron} onChange={(event) => setCron(event.target.value)} required />
        </label>
        <label>
          <span>Zona horaria IANA</span>
          <input value={timezone} onChange={(event) => setTimezone(event.target.value)} required />
        </label>
        <div className="cron-presets" aria-label="Horarios sugeridos">
          {CRON_PRESETS.map(([label, value]) => (
            <button key={value} type="button" className="button button--quiet" onClick={() => setCron(value)}>
              {label}
            </button>
          ))}
        </div>
        <button className="button button--primary" type="submit" disabled={saving}>
          {saving ? 'Guardando…' : 'Guardar programación'}
        </button>
        {feedback && <p className={`form-feedback${isError ? ' is-error' : ''}`} role="status">{feedback}</p>}
      </form>

      <div className="schedule-facts">
        <Fact label="Fuentes Bronze" value={`${data.quality_summary.fuentes_bronze_verificadas} SHA-256`} />
        <Fact label="Reglas de calidad" value={`${data.quality_summary.reglas_calidad} aplicadas`} />
        <Fact label="Rechazados" value={data.quality_summary.registros_rechazados.toLocaleString('es-CO')} />
      </div>
      <h3 className="history-heading">Ejecuciones ETL recientes</h3>
      <HistoryList runs={data.history} selectedRun={data.timing.run_id} onSelectRun={onSelectRun} />
    </section>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return <div className="schedule-fact"><span>{label}</span><strong>{value}</strong></div>;
}

function HistoryList({
  runs,
  selectedRun,
  onSelectRun,
}: {
  runs: EtlHistoryItem[];
  selectedRun: string | null;
  onSelectRun: (runId: string) => void;
}) {
  if (!runs.length) return <p className="empty-state">Aún no hay ejecuciones registradas.</p>;
  return (
    <ul className="history-list">
      {runs.map((run) => (
        <li key={run.id_ejecucion}>
          <button
            type="button"
            className={`history-button${selectedRun === run.id_ejecucion ? ' is-selected' : ''}`}
            onClick={() => onSelectRun(run.id_ejecucion)}
          >
            <span><strong>{run.id_ejecucion}</strong><small>{run.fecha_inicio ?? 'Fecha no disponible'}</small></span>
            <span className={`status-badge status-badge--${run.estado_ejecucion === 'EXITOSO' ? 'completed' : 'failed'}`}>
              {run.estado_ejecucion}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
