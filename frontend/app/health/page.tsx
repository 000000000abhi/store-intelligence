'use client';

import { useCallback } from 'react';
import { CheckCircle, XCircle, Camera, Clock } from 'lucide-react';
import { apiService } from '@/services/api';
import { usePolling } from '@/hooks/usePolling';
import { Card, StatCard } from '@/components/Card';
import { PageHeader, LoadingSpinner, ErrorBanner } from '@/components/UI';
import { StatusDot } from '@/components/Badge';
import type { HealthResponse } from '@/services/types';
import { clsx } from 'clsx';

const CAMERAS = ['CAM_ENTRY_01', 'CAM_FLOOR_01', 'CAM_FLOOR_02', 'CAM_BILL_01', 'CAM_BACK_01'];
const CAMERA_ROLES = ['Entry / F.O.H', 'Main Floor 1', 'Main Floor 2', 'Cash Counter', 'Back Room'];

function formatTimestamp(ts: string | undefined) {
  if (!ts) return '—';
  const d = new Date(ts);
  return isNaN(d.getTime()) ? '—' : d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function minutesAgo(ts: string | undefined) {
  if (!ts) return null;
  const d = new Date(ts);
  if (isNaN(d.getTime())) return null;
  return Math.floor((Date.now() - d.getTime()) / 60000);
}

export default function HealthPage() {
  const fetcher = useCallback(() => apiService.getHealth(), []);
  const { data: health, loading, error } = usePolling<HealthResponse>(fetcher, 5000);

  const isOk = health?.status?.toLowerCase() === 'ok';
  const staleWarnings = health?.stale_feed_warnings ?? [];
  const timestamps = health?.last_event_timestamps ?? {};

  return (
    <>
      <PageHeader
        title="System Health"
        subtitle="Feed freshness, camera status and service diagnostics"
        action={
          health && (
            <span className={clsx(
              'rounded-full border px-3 py-1 text-xs font-semibold',
              isOk
                ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/20 border-rose-500/30 text-rose-300'
            )}>
              {health.status}
            </span>
          )
        }
      />

      {loading && <LoadingSpinner />}
      {error && <ErrorBanner message={error} />}

      {health && (
        <>
          {/* Status Cards */}
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-3 mb-6">
            <StatCard
              label="API Status"
              value={isOk ? 'Healthy' : 'Degraded'}
              icon={isOk ? <CheckCircle size={16} /> : <XCircle size={16} />}
              trend={isOk ? 'up' : 'down'}
              color={isOk ? 'text-emerald-400' : 'text-rose-400'}
            />
            <StatCard
              label="Active Cameras"
              value={`${CAMERAS.length} / ${CAMERAS.length}`}
              icon={<Camera size={16} />}
              trend="neutral"
            />
            <StatCard
              label="Stale Feeds"
              value={staleWarnings.length}
              icon={<Clock size={16} />}
              trend={staleWarnings.length > 0 ? 'down' : 'up'}
              sub={staleWarnings.length > 0 ? '⚠ stale detected' : 'All feeds fresh'}
              color={staleWarnings.length > 0 ? 'text-amber-400' : 'text-emerald-400'}
            />
          </div>

          {/* Stale Feed Warnings */}
          {staleWarnings.length > 0 && (
            <Card className="mb-6 border-amber-500/30">
              <p className="text-sm font-semibold text-amber-300 mb-3">⚠ Stale Feed Warnings</p>
              <ul className="space-y-1">
                {staleWarnings.map((w, i) => (
                  <li key={i} className="text-sm text-slate-400">{w}</li>
                ))}
              </ul>
            </Card>
          )}

          {/* Camera Feed Status Table */}
          <Card>
            <p className="text-sm font-semibold text-slate-300 mb-4">Camera Feed Status</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-border text-slate-500 text-left">
                    <th className="pb-3 pr-6 font-medium">Camera</th>
                    <th className="pb-3 pr-6 font-medium">Role</th>
                    <th className="pb-3 pr-6 font-medium">Last Event</th>
                    <th className="pb-3 pr-6 font-medium">Minutes Ago</th>
                    <th className="pb-3 font-medium">Feed Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {CAMERAS.map((cam, i) => {
                    const ts = timestamps[cam];
                    const ago = minutesAgo(ts);
                    const stale = ago !== null && ago > 10;
                    return (
                      <tr key={cam} className="text-slate-300">
                        <td className="py-3 pr-6 font-bold text-white">{cam}</td>
                        <td className="py-3 pr-6 text-slate-400">{CAMERA_ROLES[i]}</td>
                        <td className="py-3 pr-6 font-mono text-xs text-slate-400">{formatTimestamp(ts)}</td>
                        <td className="py-3 pr-6">
                          {ago !== null ? (
                            <span className={ago > 10 ? 'text-amber-400' : 'text-slate-300'}>
                              {ago}m ago
                            </span>
                          ) : '—'}
                        </td>
                        <td className="py-3">
                          <StatusDot online={!stale && ts !== undefined} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </>
  );
}
