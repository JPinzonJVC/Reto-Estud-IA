import type {
  EtlMonitorData,
  ScheduleResponse,
  StepOutput,
  TriggerResponse,
} from '../types';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      payload && typeof payload.detail === 'string'
        ? payload.detail
        : `La solicitud falló (${response.status}).`;
    throw new Error(message);
  }
  return payload as T;
}

export const etlApi = {
  getStatus(runId?: string | null) {
    const params = runId ? `?run_id=${encodeURIComponent(runId)}` : '';
    return request<EtlMonitorData>(`/etl/monitor/status${params}`);
  },

  getStepOutput(step: { output_key: string; output_type: string }) {
    const params = new URLSearchParams({
      output_key: step.output_key,
      output_type: step.output_type,
      limit: '15',
    });
    return request<StepOutput>(`/etl/monitor/step-output?${params}`);
  },

  trigger() {
    return request<TriggerResponse>('/etl/monitor/trigger', { method: 'POST' });
  },

  updateSchedule(cron: string, timezone: string) {
    return request<ScheduleResponse>('/etl/monitor/schedule', {
      method: 'PUT',
      body: JSON.stringify({ cron, timezone }),
    });
  },
};
