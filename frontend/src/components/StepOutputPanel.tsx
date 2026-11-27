import { useEffect, useState } from 'react';
import { etlApi } from '../api/etl';
import type { EtlStep, StepOutput } from '../types';

interface StepOutputPanelProps {
  step: EtlStep | null;
}

export function StepOutputPanel({ step }: StepOutputPanelProps) {
  const [output, setOutput] = useState<StepOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!step) {
      setOutput(null);
      return;
    }
    let active = true;
    setLoading(true);
    setError(null);
    etlApi
      .getStepOutput(step)
      .then((data) => active && setOutput(data))
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Error de consulta.');
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [step?.step_id, step?.output_key, step?.output_type]);

  return (
    <section className="panel output-panel" aria-labelledby="output-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Salida inspeccionable</p>
          <h2 id="output-heading">{step?.title ?? 'Selecciona una etapa'}</h2>
        </div>
        <span className="subtle-count">{output ? `${output.total_rows} filas` : '—'}</span>
      </div>
      {!step && <p className="empty-state">Selecciona una etapa del linaje para ver sus datos.</p>}
      {loading && <p className="empty-state">Consultando la salida…</p>}
      {error && <p className="alert alert--error" role="alert">{error}</p>}
      {output && !loading && (
        <>
          {output.reconciliation && (
            <div className="quality-note">
              Reconciliación: Bronze {output.reconciliation.filas_bronze} → Silver{' '}
              {output.reconciliation.filas_silver}; rechazadas {output.reconciliation.filas_rechazadas};
              diferencia {output.reconciliation.diferencia}.
            </div>
          )}
          {output.quality_rules?.slice(0, 4).map((rule) => (
            <div className="quality-note" key={`${rule.id_incidencia}-${rule.campo}`}>
              {rule.id_incidencia} · {rule.campo}: {rule.estado} ({rule.afectados} filas)
            </div>
          ))}
          {output.columns.length === 0 || output.rows.length === 0 ? (
            <p className="empty-state">{output.note ?? 'Sin filas registradas para esta etapa.'}</p>
          ) : (
            <div className="table-scroll" tabIndex={0} aria-label="Muestra de registros de la etapa">
              <table>
                <thead><tr>{output.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
                <tbody>
                  {output.rows.map((row, index) => (
                    <tr key={index}>
                      {output.columns.map((column) => (
                        <td key={column} title={String(row[column] ?? '')}>
                          {String(row[column] ?? '—').slice(0, 50)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
