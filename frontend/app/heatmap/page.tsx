'use client';

import { useCallback } from 'react';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip,
} from 'recharts';
import { apiService } from '@/services/api';
import { usePolling } from '@/hooks/usePolling';
import { Card } from '@/components/Card';
import { PageHeader, LoadingSpinner, ErrorBanner, EmptyState } from '@/components/UI';
import type { HeatmapResponse, HeatmapZone } from '@/services/types';
import { clsx } from 'clsx';

const STORE_ID = 'STORE_BLR_002';

function ZoneBar({ zone }: { zone: HeatmapZone }) {
  const score = zone.normalized_score;
  const hue = Math.round(280 - score * 1.2); // purple (high) → blue (low)
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-slate-300 font-medium">{zone.zone_name}</span>
        <span className="text-slate-500">{Math.round(zone.avg_dwell_ms / 1000)}s avg</span>
      </div>
      <div className="h-3 w-full rounded-full bg-surface-secondary overflow-hidden">
        <div
          className="h-3 rounded-full transition-all duration-500"
          style={{
            width: `${score}%`,
            background: `hsl(${hue}, 80%, 60%)`,
            boxShadow: `0 0 8px hsl(${hue}, 80%, 60%, 0.5)`,
          }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-600">
        <span>Confidence: {zone.data_confidence.toFixed(0)}%</span>
        <span>Score: {score.toFixed(0)}/100</span>
      </div>
    </div>
  );
}

export default function HeatmapPage() {
  const fetcher = useCallback(() => apiService.getHeatmap(STORE_ID), []);
  const { data: heatmap, loading, error } = usePolling<HeatmapResponse>(fetcher, 15000);

  const zones = heatmap?.zones ?? [];
  const radarData = zones.map(z => ({
    zone: z.zone_name.replace('Z_', '').replace(/_/g, ' '),
    score: z.normalized_score,
    dwell: Math.round(z.avg_dwell_ms / 1000),
  }));

  return (
    <>
      <PageHeader
        title="Zone Heatmap"
        subtitle="Popularity and dwell time across all store zones"
      />

      {loading && <LoadingSpinner />}
      {error && <ErrorBanner message={error} />}

      {!loading && !error && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Zone Radar Chart */}
          <Card>
            <p className="text-sm font-semibold text-slate-300 mb-4">Zone Engagement Radar</p>
            {zones.length === 0 ? (
              <EmptyState label="No zone data yet." />
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#2d2148" />
                  <PolarAngleAxis dataKey="zone" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} />
                  <Radar
                    name="Engagement Score"
                    dataKey="score"
                    stroke="#d946ef"
                    fill="#d946ef"
                    fillOpacity={0.25}
                    strokeWidth={2}
                  />
                  <Tooltip
                    contentStyle={{ background: '#1e1533', border: '1px solid #2d2148', borderRadius: 12 }}
                    formatter={(v: number) => [`${v}/100`, 'Score']}
                  />
                </RadarChart>
              </ResponsiveContainer>
            )}
          </Card>

          {/* Zone Bar List */}
          <Card>
            <p className="text-sm font-semibold text-slate-300 mb-5">Zone Rankings</p>
            {zones.length === 0 ? (
              <EmptyState label="No zones to display yet." />
            ) : (
              <div className="space-y-5">
                {[...zones]
                  .sort((a, b) => b.normalized_score - a.normalized_score)
                  .map(z => <ZoneBar key={z.zone_id} zone={z} />)
                }
              </div>
            )}
          </Card>

          {/* Store Floor Plan Visual */}
          <Card className="lg:col-span-2">
            <p className="text-sm font-semibold text-slate-300 mb-4">Store Floor — Zone Layout</p>
            <div className="relative h-48 rounded-xl overflow-hidden border border-surface-border bg-surface-secondary">
              {/* Simplified store grid */}
              <div className="absolute inset-0 grid grid-cols-9 grid-rows-3 gap-1 p-3 text-[10px] font-bold">
                {['EB Korean','Face Shop','Good Vibes','DermDoc','Minimalist','Aqualogica','Lakme Skin','Accessories','–']
                  .map(z => (
                    <div key={z} className="flex items-center justify-center rounded bg-brand-600/20 text-brand-300 border border-brand-500/20 text-center leading-tight p-1">
                      {z}
                    </div>
                  ))
                }
                {['Fragrance','Nail Unit','–','F.O.H','F.O.H','Makeup','Makeup','Cash Counter','PMU']
                  .map(z => (
                    <div key={z} className={clsx(
                      'flex items-center justify-center rounded border text-center leading-tight p-1',
                      z === 'Cash Counter'
                        ? 'bg-emerald-600/30 text-emerald-300 border-emerald-500/30 animate-pulse'
                        : z === 'F.O.H'
                        ? 'bg-slate-600/20 text-slate-400 border-slate-500/20'
                        : 'bg-brand-600/20 text-brand-300 border-brand-500/20'
                    )}>
                      {z}
                    </div>
                  ))
                }
                {['Maybelline','Faces Canada','Lakme','Colorbar+Sugar','Swiss Beauty','Renee+NY Bae','Alps Goodness','Streax','–']
                  .map(z => (
                    <div key={z} className="flex items-center justify-center rounded bg-brand-600/20 text-brand-300 border border-brand-500/20 text-center leading-tight p-1">
                      {z}
                    </div>
                  ))
                }
              </div>
              <div className="absolute right-2 bottom-2 text-xs text-slate-600">🟢 Billing Zone</div>
            </div>
          </Card>
        </div>
      )}
    </>
  );
}
