'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const nav = [
  { href: '/', label: 'Console' },
  { href: '/trades', label: 'Trades' },
  { href: '/backtest', label: 'Backtest' },
  { href: '/rules', label: 'Rules' },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-ink-line bg-ink">
      <div className="border-b border-ink-line px-5 py-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-gold-bright to-gold-dim font-bold text-ink">
            Au
          </div>
          <div>
            <div className="text-sm font-bold tracking-wide">JARVES</div>
            <div className="text-[10px] uppercase tracking-[0.15em] text-muted">Gold agent</div>
          </div>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-3">
        {nav.map(({ href, label }) => {
          const active = href === '/' ? pathname === '/' : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'rounded-lg px-3 py-2 text-sm transition-colors',
                active
                  ? 'bg-gold/10 font-semibold text-gold'
                  : 'text-muted hover:bg-ink-raised hover:text-paper',
              )}
            >
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-ink-line px-5 py-4 text-[11px] leading-relaxed text-muted">
        XAU/USD only. Rule-based, no forecasting.
      </div>
    </aside>
  );
}
