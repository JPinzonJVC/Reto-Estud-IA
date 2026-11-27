import type { MlCase, MlOverview, MlResultPage } from '../types';

export interface MlQuery {
  limit?: number;
  offset?: number;
  company?: string;
  segment?: string;
}

async function request<T>(url: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { headers: { Accept: 'application/json' } });
  } catch {
    throw new Error('No se pudo conectar con la API de ACTHO 360.');
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message = typeof detail === 'string' ? detail : `La consulta falló (${response.status}).`;
    throw new Error(message);
  }
  return payload as T;
}

export const mlApi = {
  overview() {
    return request<MlOverview>('/ml/resumen');
  },

  results(caso: MlCase, query: MlQuery = {}) {
    const params = new URLSearchParams({
      limit: String(query.limit ?? 12),
      offset: String(query.offset ?? 0),
    });
    if (query.company) params.set('buscar_empresa', query.company);
    if (query.segment) params.set('segmento', query.segment);
    return request<MlResultPage>(`/ml/resultados/${caso}?${params.toString()}`);
  },
};
