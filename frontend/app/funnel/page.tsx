'use client';

import { useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell, LabelList,
} from 'recharts';
import { apiService } from '@/services/api';
import { usePolling } from '@/hooks/usePolling';
import { Card } from '@/components/Card';
import { PageHeader, LoadingSpinner, ErrorBanner, EmptyState } from '@/components/UI';
import type { FunnelResponse } from '@/services/types';

const STORE_ID = 'STORE_BLR_002';

const STAGE_COLORS = [
  '#d946ef', // ENTRY        — brand purple
  '#a855f7', // ZONE_VISIT   — lighter purple
  '#6366f1', // BILLING_QUEUE — indigo
  '#10b981', // PURCHASE     — emerald (success)
];

const STAGE_LABELS: Record<string, string> = {
  entry:         'Entry',
  zone_visit:    'Zone Visit',
  billing_queue: 'Billing Queue',
  purchase:      'Purchase',
};

export default function FunnelPage() {
  const fetcher = useCallback(() => apiService.getFunnel(STORE_ID), []);
  const { data: funnel, loading, error } = usePolling<FunnelResponse>(fetcher, 15000);

  // Backend returns a bare FunnelStage[]
  const stages = funnel ?? [];
  const hasData = stages.some(s => s.count > 0);

  // Transform for Recharts Funnel
  const funnelData = stages.map((s, i) => ({
    name: STAGE_LABELS[s.stage] ?? s.stage,
    value: s.count,
    fill: STAGE_COLORS[i % STAGE_COLORS.length],
  }));

  // Transform for drop-off bar chart
  const dropoffData = stages
    .filter(s => s.drop_off_percentage > 0)
    .map((s, i) => ({
      name: STAGE_LABELS[s.stage] ?? s.stage,
      dropOff: parseFloat(s.drop_off_percentage.toFixed(1)),
      fill: STAGE_COLORS[i % STAGE_COLORS.length],
    }));

  return (
    <>
      <PageHeader
        title="Conversion Funnel"
        subtitle="Session-based journey from entry to purchase"
      />

      {loading && <LoadingSpinner />}
      {error && <ErrorBanner message={error} />}

      {!loading && !error && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Funnel Chart */}
          <Card>
            <p className="text-sm font-semibold text-slate-300 mb-4">Visitor Funnel</p>
            {!hasData ? (
              <EmptyState label="No funnel data yet. Start ingesting events." />
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={funnelData} layout="vertical" barCategoryGap="30%">
                  <CartesianGrid strokeDasharray="3 3" stroke="#2d2148" horizontal={false} />
                  <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} width={110} />
                  <Tooltip
                    contentStyle={{ background: '#1e1533', border: '1px solid #2d2148', borderRadius: 12 }}
                    formatter={(v: number) => [v, 'Visitors']}
                  />
                  <Bar dataKey="value" radius={[0, 8, 8, 0]}>
                    {funnelData.map((entry, index) => (
                      <Cell key={index} fill={entry.fill} />
                    ))}
                    <LabelList dataKey="value" position="right" fill="#94a3b8" style={{ fontSize: 12 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>

          {/* Drop-off Bar Chart */}
          <Card>
            <p className="text-sm font-semibold text-slate-300 mb-4">Stage Drop-off (%)</p>
            {dropoffData.length === 0 ? (
              <EmptyState label="No drop-off data available." />
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={dropoffData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#2d2148" horizontal={false} />
                  <XAxis type="number" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} domain={[0, 100]} />
                  <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} axisLine={false} tickLine={false} width={100} />
                  <Tooltip
                    contentStyle={{ background: '#1e1533', border: '1px solid #2d2148', borderRadius: 12 }}
                    formatter={(v: number) => [`${v}%`, 'Drop-off']}
                  />
                  <Bar dataKey="dropOff" radius={[0, 6, 6, 0]}>
                    {dropoffData.map((entry, index) => (
                      <Cell key={index} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>

          {/* Stage Breakdown Table */}
          <Card className="lg:col-span-2">
            <p className="text-sm font-semibold text-slate-300 mb-4">Stage Breakdown</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-border text-slate-500 text-left">
                    <th className="pb-3 pr-6 font-medium">Stage</th>
                    <th className="pb-3 pr-6 font-medium">Count</th>
                    <th className="pb-3 pr-6 font-medium">Drop-off</th>
                    <th className="pb-3 font-medium">Conversion</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {stages.map((s, i) => {
                    const maxCount = stages[0]?.count ?? 1;
                    const pct = maxCount > 0 ? ((s.count / maxCount) * 100).toFixed(1) : '0.0';
                    return (
                      <tr key={s.stage} className="text-slate-300">
                        <td className="py-3 pr-6 flex items-center gap-2">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ background: STAGE_COLORS[i] }} />
                          {STAGE_LABELS[s.stage] ?? s.stage}
                        </td>
                        <td className="py-3 pr-6 font-bold text-white">{s.count}</td>
                        <td className="py-3 pr-6 text-rose-400">
                          {s.drop_off_percentage > 0 ? `${s.drop_off_percentage.toFixed(1)}%` : '—'}
                        </td>
                        <td className="py-3">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-surface-secondary rounded-full h-1.5 max-w-32">
                              <div
                                className="h-1.5 rounded-full"
                                style={{ width: `${pct}%`, background: STAGE_COLORS[i] }}
                              />
                            </div>
                            <span className="text-xs text-slate-400">{pct}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </>
  );
}
