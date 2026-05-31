export interface MetricsResponse {
  store_id: string;
  date: string;
  unique_visitors: number;
  conversion_rate: number;
  avg_dwell_by_zone: Record<string, number>;
  avg_dwell_ms: number;           // Overall average dwell ms across all sessions
  queue_depth: number;
  abandonment_rate: number;
  computed_at: string;
}

export interface FunnelStage {
  stage: string;
  count: number;
  drop_off_percentage: number;    // Aligned with backend field name
}

// Backend returns a bare array of FunnelStage (no wrapper object)
export type FunnelResponse = FunnelStage[];

export interface HeatmapZone {
  zone_id: string;
  zone_name: string;
  avg_dwell_ms: number;
  normalized_score: number;
  data_confidence: number;
}

export interface HeatmapResponse {
  store_id: string;
  zones: HeatmapZone[];
  data_confidence: string;
}

export interface AnomalyItem {
  type: string;
  severity: 'INFO' | 'WARN' | 'CRITICAL';
  description: string;
  suggested_action: string;
  triggered_at: string;
}

export interface AnomaliesResponse {
  store_id: string;
  anomalies: AnomalyItem[];         // Backend returns anomalies (not active_anomalies)
}

export interface HealthResponse {
  status: string;
  database: string;
  stores: string[];
  stale_feed_warnings: string[];
  last_event_timestamps: Record<string, string>;
}
