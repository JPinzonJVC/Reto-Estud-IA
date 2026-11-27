import type { EtlStep } from '../types';
import { StatusBadge } from './StatusBadge';

interface EtlStepListProps {
  steps: EtlStep[];
  selectedId: string | null;
  onSelect: (step: EtlStep) => void;
}

export function EtlStepList({ steps, selectedId, onSelect }: EtlStepListProps) {
  return (
    <section className="panel etl-steps-panel" aria-labelledby="steps-heading">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Linaje DWH Medallion</p>
          <h2 id="steps-heading">Etapas del flujo</h2>
        </div>
        <span className="subtle-count">{steps.length} etapas</span>
      </div>
      <p className="description">
        Selecciona una etapa para consultar la salida guardada, sus reglas de calidad y la
        reconciliación de registros.
      </p>
      <ol className="step-list">
        {steps.map((step) => (
          <li key={step.step_id}>
            <button
              type="button"
              className={`step-button${selectedId === step.step_id ? ' is-selected' : ''}`}
              onClick={() => onSelect(step)}
              aria-pressed={selectedId === step.step_id}
            >
              <span className={`step-dot step-dot--${step.status.toLowerCase()}`} />
              <span className="step-content">
                <span className="step-title">
                  <span className="step-order">{String(step.order).padStart(2, '0')}</span>
                  <span>{step.title}</span>
                  <StatusBadge status={step.status} />
                  <span className="layer-badge">{step.layer}</span>
                </span>
                <span className="step-subtitle">{step.subtitle}</span>
              </span>
              <span className="step-count">
                {step.registros_insertados.toLocaleString('es-CO')} reg.
              </span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}
