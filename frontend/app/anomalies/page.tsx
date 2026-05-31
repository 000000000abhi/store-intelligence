'use client';

import { useCallback } from 'react';
import { AlertTriangle, ShieldAlert, Info, CheckCircle } from 'lucide-react';
import { apiService } from '@/services/api';
import { usePolling } from '@/hooks/usePolling';
import { Card } from '@/components/Card';
import { PageHeader, LoadingSpinner, ErrorBanner, EmptyState } from '@/components/UI';
import { SeverityBadge } from '@/components/Badge';
import type { AnomaliesResponse, AnomalyItem } from '@/services/types';

const STORE_ID = 'STORE_BLR_002';

const ANOMALY_META: Record<string, { icon: React.ReactNode; label: string }> = {
  QUEUE_SPIKE:      { icon: <AlertTriangle size={18} />, label: 'Queue Spike' },
  CONVERSION_DROP:  { icon: <ShieldAlert size={18} />,  label: 'Conversion Drop' },
  DEAD_ZONE:        { icon: <Info size={18} />,          label: 'Dead Zone' },
  STALE_FEED:       { icon: <AlertTriangle size={18} />, label: 'Stale Feed' },
};

function AnomalyCard({ anomaly }: { anomaly: AnomalyItem }) {
  const meta = ANOMALY_META[anomaly.type] ?? { icon: <Info size={18} />, label: anomaly.type };
  const borderColor =
    anomaly.severity === 'CRITICAL' ? 'border-rose-500/40'
    : anomaly.severity === 'WARN'   ? 'border-amber-500/40'
    :                                  'border-sky-500/40';

  const iconBg =
    anomaly.severity === 'CRITICAL' ? 'bg-rose-500/20 text-rose-400'
    : anomaly.severity === 'WARN'   ? 'bg-amber-500/20 text-amber-400'
    :                                  'bg-sky-500/20 text-sky-400';

  const triggeredAt = new Date(anomaly.triggered_at);
  const timeStr = isNaN(triggeredAt.getTime())
    ? '—'
    : triggeredAt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

  return (
    <div className={`rounded-2xl border bg-surface-card p-5 flex gap-4 items-start transition-all duration-200 hover:shadow-lg ${borderColor}`}>
      <div className={`mt-0.5 flex-none rounded-xl p-2.5 ${iconBg}`}>
        {meta.icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold text-white text-sm">{meta.label}</span>
          <SeverityBadge severity={anomaly.severity} />
        </div>
        <p className="text-sm text-slate-300 mb-2">{anomaly.description}</p>
        <div className="flex items-start gap-1.5">
          <CheckCircle size={13} className="mt-0.5 flex-none text-emerald-400" />
          <p className="text-xs text-slate-400">{anomaly.suggested_action}</p>
        </div>
      </div>
      <span className="flex-none text-xs text-slate-500 mt-0.5">{timeStr}</span>
    </div>
  );
}

export default function AnomaliesPage() {
  const fetcher = useCallback(() => apiService.getAnomalies(STORE_ID), []);
  const { data: anomalies, loading, error } = usePolling<AnomaliesResponse>(fetcher, 10000);

  const items = anomalies?.anomalies ?? [];
  const criticals = items.filter(a => a.severity === 'CRITICAL');
  const warns = items.filter(a => a.severity === 'WARN');
  const infos = items.filter(a => a.severity === 'INFO');

  return (
    <>
      <PageHeader
        title="Active Anomalies"
        subtitle={`${items.length} active alerts · refreshed every 10s`}
        action={
          items.length > 0 ? (
            <span className="rounded-full bg-rose-500/20 border border-rose-500/30 px-3 py-1 text-xs font-semibold text-rose-300 animate-pulse">
              {items.length} Alert{items.length > 1 ? 's' : ''}
            </span>
          ) : (
            <span className="rounded-full bg-emerald-500/20 border border-emerald-500/30 px-3 py-1 text-xs font-semibold text-emerald-300">
              All Clear
            </span>
          )
        }
      />

      {loading && <LoadingSpinner />}
      {error && <ErrorBanner message={error} />}

      {!loading && !error && (
        <>
          {/* Summary Row */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <Card className="text-center">
              <p className="text-2xl font-bold text-rose-400">{criticals.length}</p>
              <p className="text-xs text-slate-500 mt-1 uppercase tracking-widest">Critical</p>
            </Card>
            <Card className="text-center">
              <p className="text-2xl font-bold text-amber-400">{warns.length}</p>
              <p className="text-xs text-slate-500 mt-1 uppercase tracking-widest">Warnings</p>
            </Card>
            <Card className="text-center">
              <p className="text-2xl font-bold text-sky-400">{infos.length}</p>
              <p className="text-xs text-slate-500 mt-1 uppercase tracking-widest">Info</p>
            </Card>
          </div>

          {/* Anomaly List */}
          {items.length === 0 ? (
            <Card>
              <EmptyState label="No active anomalies. Store is running normally." />
            </Card>
          ) : (
            <div className="space-y-3">
              {[...criticals, ...warns, ...infos].map((a, i) => (
                <AnomalyCard key={i} anomaly={a} />
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
