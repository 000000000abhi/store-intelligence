import type { ReactNode } from 'react';
import { clsx } from 'clsx';

interface CardProps {
  children: ReactNode;
  className?: string;
  glowing?: boolean;
}

export function Card({ children, className, glowing }: CardProps) {
  return (
    <div
      className={clsx(
        'rounded-2xl border border-surface-border bg-surface-card p-6 transition-all duration-200',
        glowing && 'shadow-lg shadow-brand-500/10 border-brand-500/30',
        className
      )}
    >
      {children}
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
}

export function StatCard({ label, value, sub, icon, trend, color }: StatCardProps) {
  const trendColor =
    trend === 'up' ? 'text-emerald-400' :
    trend === 'down' ? 'text-rose-400' :
    'text-slate-400';

  return (
    <Card className="flex flex-col gap-3 hover:border-brand-500/40 hover:shadow-brand-500/10 hover:shadow-lg">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-slate-500">{label}</span>
        {icon && (
          <span className={clsx('p-2 rounded-xl bg-surface-secondary', color ?? 'text-brand-400')}>
            {icon}
          </span>
        )}
      </div>
      <div className="flex items-end gap-2">
        <span className="text-3xl font-bold text-white">{value}</span>
        {sub && <span className={clsx('mb-1 text-sm font-medium', trendColor)}>{sub}</span>}
      </div>
    </Card>
  );
}
