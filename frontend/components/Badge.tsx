'use client';

import { clsx } from 'clsx';

interface BadgeProps {
  severity: 'INFO' | 'WARN' | 'CRITICAL';
  label?: string;
}

export function SeverityBadge({ severity, label }: BadgeProps) {
  const styles = {
    INFO:     'bg-sky-500/20 text-sky-300 border-sky-500/30',
    WARN:     'bg-amber-500/20 text-amber-300 border-amber-500/30',
    CRITICAL: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
  };

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold',
        styles[severity]
      )}
    >
      <span className={clsx(
        'h-1.5 w-1.5 rounded-full',
        severity === 'CRITICAL' && 'animate-pulse bg-rose-400',
        severity === 'WARN'     && 'bg-amber-400',
        severity === 'INFO'     && 'bg-sky-400',
      )} />
      {label ?? severity}
    </span>
  );
}

interface StatusDotProps {
  online: boolean;
}
export function StatusDot({ online }: StatusDotProps) {
  return (
    <span className="flex items-center gap-2 text-sm font-medium">
      <span className={clsx(
        'h-2 w-2 rounded-full',
        online ? 'bg-emerald-400 shadow-emerald-400/50 shadow-sm animate-pulse' : 'bg-rose-400'
      )} />
      {online ? 'Live' : 'Disconnected'}
    </span>
  );
}
