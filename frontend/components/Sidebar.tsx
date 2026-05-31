'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  TrendingDown,
  Map,
  AlertTriangle,
  Activity,
} from 'lucide-react';
import { clsx } from 'clsx';
import { StatusDot } from './Badge';
import { useStoreWebSocket } from '@/hooks/useWebSocket';

const NAV_ITEMS = [
  { href: '/',           label: 'Overview',  icon: LayoutDashboard },
  { href: '/funnel',     label: 'Funnel',    icon: TrendingDown },
  { href: '/heatmap',    label: 'Heatmap',   icon: Map },
  { href: '/anomalies',  label: 'Anomalies', icon: AlertTriangle },
  { href: '/health',     label: 'Health',    icon: Activity },
];

const STORE_ID = 'STORE_BLR_002';

export function Sidebar() {
  const pathname = usePathname();
  const { connected } = useStoreWebSocket(STORE_ID);

  return (
    <aside className="flex w-64 flex-none flex-col border-r border-surface-border bg-surface-secondary">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-6 border-b border-surface-border">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 shadow-lg shadow-brand-500/30">
          <span className="text-base font-black text-white">SI</span>
        </div>
        <div>
          <p className="text-sm font-bold text-white">Store Intel</p>
          <p className="text-xs text-slate-500">Brigade Road</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150',
                active
                  ? 'bg-brand-600/20 text-brand-300 shadow-inner border border-brand-500/20'
                  : 'text-slate-400 hover:bg-surface-card hover:text-white'
              )}
            >
              <Icon size={18} className={active ? 'text-brand-400' : ''} />
              {label}
              {label === 'Anomalies' && (
                <span className="ml-auto h-2 w-2 rounded-full bg-rose-400 animate-pulse" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Live Status */}
      <div className="border-t border-surface-border px-6 py-4">
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-500">Real-time Feed</span>
          <StatusDot online={connected} />
        </div>
        <p className="mt-1 text-xs text-slate-600">{STORE_ID} · CAM 1-5</p>
      </div>
    </aside>
  );
}
