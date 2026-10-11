import { HealthStatus, SystemStatus, ExperimentRecord, RunRecord, SimEvent, AnalyticsSummaryResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_URL || '';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!resp.ok) {
    let errorMsg = `HTTP ${resp.status} ${resp.statusText}`;
    try {
      const err = await resp.json();
      if (err.detail) errorMsg = err.detail;
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }
  return resp.json();
}

export const api = {
  getHealth: () => fetchJson<HealthStatus>('/api/health'),
  getReady: () => fetchJson<{ ready: boolean }>('/api/ready'),
  getSystemStatus: () => fetchJson<SystemStatus>('/api/system/status'),
  getPresets: () => fetchJson<{ difficulty_presets: any; fault_presets: any }>('/api/presets'),
  
  createExperiment: (payload: any) =>
    fetchJson<{ experiment_id: string; status: string }>('/api/experiments', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listExperiments: (params?: { limit?: number; offset?: number; status?: string; agent_type?: string; search?: string }) => {
    const sp = new URLSearchParams();
    if (params?.limit) sp.set('limit', String(params.limit));
    if (params?.offset) sp.set('offset', String(params.offset));
    if (params?.status) sp.set('status', params.status);
    if (params?.agent_type) sp.set('agent_type', params.agent_type);
    if (params?.search) sp.set('search', params.search);
    return fetchJson<{ experiments: ExperimentRecord[]; count: number }>(`/api/experiments?${sp.toString()}`);
  },

  getExperiment: (id: string) => fetchJson<ExperimentRecord>(`/api/experiments/${id}`),
  cancelExperiment: (id: string) => fetchJson<{ experiment_id: string; cancelled: boolean }>(`/api/experiments/${id}/cancel`, { method: 'POST' }),
  deleteExperiment: (id: string) => fetchJson<{ experiment_id: string; deleted: boolean }>(`/api/experiments/${id}`, { method: 'DELETE' }),
  rerunFailedRuns: (id: string) => fetchJson<{ new_experiment_id: string; seeds: number[]; status: string }>(`/api/experiments/${id}/rerun-failed`, { method: 'POST' }),

  listRuns: (expId: string) => fetchJson<{ runs: RunRecord[]; count: number }>(`/api/experiments/${expId}/runs`),
  getRun: (runId: string) => fetchJson<RunRecord>(`/api/runs/${runId}`),
  getRunEvents: (runId: string, minSeq: number = 0, limit: number = 500, type?: string) => {
    const sp = new URLSearchParams({ min_seq: String(minSeq), limit: String(limit) });
    if (type) sp.set('type', type);
    return fetchJson<{ events: SimEvent[]; count: number }>(`/api/runs/${runId}/events?${sp.toString()}`);
  },
  getMessageLifecycle: (runId: string, msgId: string) =>
    fetchJson<{ msg_id: string; lifecycle: SimEvent[] }>(`/api/runs/${runId}/messages/${msgId}/lifecycle`),

  getAnalyticsSummary: (expId?: string, pairedFaultFreeOnly: boolean = false) => {
    const sp = new URLSearchParams();
    if (expId) sp.set('experiment_id', expId);
    if (pairedFaultFreeOnly) sp.set('paired_fault_free_only', 'true');
    return fetchJson<AnalyticsSummaryResponse>(`/api/analytics/summary?${sp.toString()}`);
  },

  testLlmConnection: (payload: { gemini_api_key?: string; provider_model?: string }) =>
    fetchJson<{ success: boolean; configured: boolean; message: string; model?: string }>('/api/llm/test-connection', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getExportExperimentUrl: (expId: string) => `${BASE_URL}/api/experiments/${expId}/export.csv`,
  getExportEventsUrl: (runId: string) => `${BASE_URL}/api/runs/${runId}/events.csv`,
};
