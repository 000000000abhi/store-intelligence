'use client';

import { useCallback } from 'react';
import {
  Users, ShoppingBag, Clock, List, TrendingDown, Activity,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';

import { apiService } from '@/services/api';
import { usePolling } from '@/hooks/usePolling';
import { useStoreWebSocket } from '@/hooks/useWebSocket';
import { StatCard } from '@/components/Card';
import { PageHeader, LoadingSpinner, ErrorBanner } from '@/components/UI';
import type { MetricsResponse } from '@/services/types';

const STORE_ID = 'STORE_BLR_002';

// Sparkline mock — replaced by live data in production
const MOCK_TREND = Array.from({ length: 12 }, (_, i) => ({
  t: `${8 + i}:00`,
  visitors: Math.floor(Math.random() * 30 + 5),
}));

function msToMinSec(ms: number) {
  const s = Math.round(ms / 1000);
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}m ${s % 60}s` : `${s}s`;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-surface-border bg-surface-card px-4 py-2 text-sm shadow-xl">
      <p className="text-slate-400">{label}</p>
      <p className="font-semibold text-brand-300">{payload[0].value} visitors</p>
    </div>
  );
};

export default function OverviewPage() {
  const fetcher = useCallback(() => apiService.getMetrics(STORE_ID), []);
  const { data: metrics, loading, error } = usePolling<MetricsResponse>(fetcher, 10000);
  const { connected } = useStoreWebSocket(STORE_ID);

  return (
    <>
      <PageHeader
        title="Store Overview"
        subtitle={`Brigade Road · ${connected ? '🟢 Live' : '🔴 Offline'}`}
        action={
          <span className="rounded-full bg-brand-600/20 border border-brand-500/20 px-3 py-1 text-xs font-semibold text-brand-300">
            {new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
          </span>
        }
      />

      {loading && <LoadingSpinner />}
      {error && <ErrorBanner message={error} />}

      {metrics && (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 gap-5 lg:grid-cols-3 mb-8">
            <StatCard
              label="Unique Visitors"
              value={metrics.unique_visitors}
              icon={<Users size={16} />}
              trend="up"
              sub="+12% vs avg"
            />
            <StatCard
              label="Conversion Rate"
              value={`${(metrics.conversion_rate * 100).toFixed(1)}%`}
              icon={<ShoppingBag size={16} />}
              trend={metrics.conversion_rate > 0.3 ? 'up' : 'down'}
              sub={metrics.conversion_rate < 0.3 ? '▼ below baseline' : '▲ on track'}
            />
            <StatCard
              label="Avg Dwell Time"
              value={metrics.avg_dwell_ms > 0 ? msToMinSec(metrics.avg_dwell_ms) : '—'}
              icon={<Clock size={16} />}
              trend="neutral"
            />
            <StatCard
              label="Queue Depth"
              value={metrics.queue_depth.toFixed(1)}
              icon={<Activity size={16} />}
              trend={metrics.queue_depth > 5 ? 'down' : 'neutral'}
              sub={metrics.queue_depth > 5 ? '⚠ spike detected' : 'Normal'}
              color={metrics.queue_depth > 5 ? 'text-amber-400' : 'text-emerald-400'}
            />
            <StatCard
              label="Abandonment Rate"
              value={`${(metrics.abandonment_rate * 100).toFixed(1)}%`}
              icon={<TrendingDown size={16} />}
              trend={metrics.abandonment_rate > 0.4 ? 'down' : 'up'}
            />
            <StatCard
              label="Billing Conversions"
              value={`${Math.round(metrics.unique_visitors * metrics.conversion_rate)}`}
              icon={<ShoppingBag size={16} />}
              trend="neutral"
              sub="POS correlated"
            />
          </div>

          {/* Visitor Trend Sparkline */}
          <div className="rounded-2xl border border-surface-border bg-surface-card p-6">
            <p className="text-sm font-semibold text-slate-300 mb-4">Visitor Traffic — Hourly Trend</p>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={MOCK_TREND}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d2148" />
                <XAxis dataKey="t" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="visitors"
                  stroke="#d946ef"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 5, fill: '#d946ef' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {!loading && !error && !metrics && (
        <div className="text-center py-20 text-slate-500">
          <p className="text-5xl mb-4">📡</p>
          <p>No metrics yet. Start the pipeline to begin ingesting events.</p>
        </div>
      )}
    </>
  );
}
