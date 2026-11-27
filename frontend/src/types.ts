export interface EtlStep {
  order: number;
  step_id: string;
  title: string;
  subtitle: string;
  layer: string;
  fuente: string;
  status: string;
  duration_seconds: number | null;
  registros_leidos: number;
  registros_insertados: number;
  registros_rechazados: number;
  output_type: 'table' | 'watermark';
  output_key: string;
}

export interface EtlHistoryItem {
  id_ejecucion: string;
  fecha_inicio: string | null;
  fecha_finalizacion: string | null;
  archivos_procesados: number;
  registros_leidos: number;
  registros_cargados: number;
  estado_ejecucion: string;
}

export interface EtlMonitorData {
  flow: {
    name: string;
    deployment: string;
    schedule_cron: string;
    schedule_timezone: string;
    schedule_label: string;
    prefect_connected: boolean;
    prefect_live_runs: number;
    prefect_latest_run_name: string | null;
    prefect_latest_run_id?: string | null;
    prefect_latest_state: string | null;
    prefect_latest_message: string | null;
    prefect_skipped_no_changes: boolean;
    fuente_auditoria: string;
  };
  timing: {
    run_id: string | null;
    status: string;
    last_run_start: string | null;
    last_run_end: string | null;
    last_run_ago: string;
    elapsed_seconds: number | null;
    next_run_iso: string | null;
    next_run_in: string;
  };
  progress: {
    percent: number;
    completed_steps: number;
    total_steps: number;
    registros_leidos: number;
    registros_cargados: number;
    registros_rechazados: number;
  };
  steps: EtlStep[];
  history: EtlHistoryItem[];
  quality_summary: {
    reglas_calidad: number;
    registros_rechazados: number;
    fuentes_bronze_verificadas: number;
  };
}

export interface StepOutput {
  total_rows: number;
  columns: string[];
  rows: Array<Record<string, string | number | null>>;
  note?: string | null;
  quality_rules?: Array<{
    id_incidencia: string;
    campo: string;
    estado: string;
    afectados: number;
  }>;
  reconciliation?: {
    filas_bronze: number;
    filas_silver: number;
    filas_rechazadas: number;
    diferencia: number;
  } | null;
}

export interface TriggerResponse {
  modo: string;
  flow_run_id?: string | null;
  run_id?: string | null;
  state?: string;
}

export interface ScheduleResponse {
  schedule_label: string;
  next_run_iso: string;
  next_run_in: string;
}

export type MlCase =
  | 'fidelidad_rfm_s'
  | 'recomendacion_linea'
  | 'churn_heuristico'
  | 'lead_prioridad';

export interface MlResult {
  id_empresa: string;
  id_ejecucion: string;
  caso_uso: MlCase;
  version: string;
  fecha_corte: string;
  estado: string;
  metodo: string;
  score: number | null;
  segmento_o_linea: string | null;
  soporte: number | null;
  justificacion: Record<string, unknown>;
  metricas: Record<string, unknown>;
}

export interface MlResultPage {
  caso_uso: MlCase;
  fecha_corte: string | null;
  version: string | null;
  id_ejecucion: string | null;
  total: number;
  limit: number;
  offset: number;
  items: MlResult[];
}

export interface MlOverviewCase {
  caso_uso: MlCase;
  fecha_corte: string | null;
  version: string | null;
  estado: string;
  empresas_procesadas: number;
  resultados_disponibles: number;
  tipo_resultado: string;
}

export interface MlOverview {
  fecha_corte: string | null;
  resultados_totales: number;
  modelos_aprobados_disponibles: number;
  casos_uso: MlOverviewCase[];
}
