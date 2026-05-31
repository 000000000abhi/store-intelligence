import type {
  MetricsResponse,
  FunnelResponse,
  HeatmapResponse,
  AnomaliesResponse,
  HealthResponse,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    next: { revalidate: 0 }, // Always fresh
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json() as Promise<T>;
}

export const apiService = {
  getMetrics:   (storeId: string) => apiFetch<MetricsResponse>(`/stores/${storeId}/metrics`),
  getFunnel:    (storeId: string) => apiFetch<FunnelResponse>(`/stores/${storeId}/funnel`),
  getHeatmap:   (storeId: string) => apiFetch<HeatmapResponse>(`/stores/${storeId}/heatmap`),
  getAnomalies: (storeId: string) => apiFetch<AnomaliesResponse>(`/stores/${storeId}/anomalies`),
  getHealth:    ()                => apiFetch<HealthResponse>('/health'),
};
