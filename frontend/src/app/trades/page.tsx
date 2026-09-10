'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '@/lib/api';
import { Card, Empty, Pill, Stat } from '@/components/ui';
import { dateTimeOf, money, pct, price, signedMoney } from '@/lib/utils';
import type { Performance, Trade } from '@/types';

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [stats, setStats] = useState<Performance | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [nextTrades, nextStats] = await Promise.all([api.trades(200), api.performance()]);
      setTrades(nextTrades);
      setStats(nextStats);
      setError('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 15_000);
    return () => clearInterval(timer);
  }, [load]);

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <header>
        <h1 className="text-xl font-semibold">Trades</h1>
        <p className="text-sm text-muted">Everything the agent has actually done, and what it earned.</p>
      </header>

      {error && (
        <div className="rounded-lg border border-down/40 bg-down/10 px-4 py-3 text-sm text-down">{error}</div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        <Stat label="Trades" value={stats?.trades ?? 0} />
        <Stat label="Win rate" value={pct(stats?.win_rate ?? 0, 1)} />
        <Stat
          label="Net P&L"
          value={signedMoney(stats?.total_pnl ?? 0)}
          tone={(stats?.total_pnl ?? 0) >= 0 ? 'up' : 'down'}
        />
        <Stat label="Profit factor" value={(stats?.profit_factor ?? 0).toFixed(2)} />
        <Stat label="Expectancy" value={`${(stats?.expectancy_r ?? 0).toFixed(2)}R`} />
        <Stat label="Worst streak" value={stats?.max_consecutive_losses ?? 0} />
      </div>

      {stats && Object.keys(stats.by_session).length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card title="By session">
            <div className="space-y-2">
              {Object.entries(stats.by_session).map(([name, row]) => (
                <div key={name} className="flex items-center justify-between text-sm">
                  <span className="text-muted">{name}</span>
                  <span className="font-mono">
                    {row.trades} trades · {pct(row.win_rate, 0)} ·{' '}
                    <span className={row.pnl >= 0 ? 'text-up' : 'text-down'}>
                      {signedMoney(row.pnl)}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </Card>
          <Card title="How trades ended">
            <div className="space-y-2">
              {Object.entries(stats.by_exit_reason).map(([reason, count]) => (
                <div key={reason} className="flex items-center justify-between text-sm">
                  <span className="text-muted">{reason}</span>
                  <span className="font-mono">{count}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      <Card title="History">
        {trades.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px] text-sm">
              <thead>
                <tr className="border-b border-ink-line text-left text-[11px] uppercase tracking-wider text-muted">
                  <th className="px-2 py-2 font-medium">Opened</th>
                  <th className="px-2 py-2 font-medium">Side</th>
                  <th className="px-2 py-2 text-right font-medium">Units</th>
                  <th className="px-2 py-2 text-right font-medium">Entry</th>
                  <th className="px-2 py-2 text-right font-medium">Stop</th>
                  <th className="px-2 py-2 text-right font-medium">Exit</th>
                  <th className="px-2 py-2 font-medium">Reason</th>
                  <th className="px-2 py-2 text-right font-medium">R</th>
                  <th className="px-2 py-2 text-right font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => (
                  <tr key={trade.id} className="border-b border-ink-line/60 last:border-0">
                    <td className="px-2 py-2 text-muted">{dateTimeOf(trade.opened_at)}</td>
                    <td className="px-2 py-2">
                      <Pill tone={trade.direction === 'LONG' ? 'up' : 'down'}>{trade.direction}</Pill>
                    </td>
                    <td className="px-2 py-2 text-right font-mono">{trade.units}</td>
                    <td className="px-2 py-2 text-right font-mono">{price(trade.entry_price)}</td>
                    <td className="px-2 py-2 text-right font-mono text-muted">{price(trade.stop_loss)}</td>
                    <td className="px-2 py-2 text-right font-mono">
                      {trade.exit_price ? price(trade.exit_price) : <span className="text-gold">open</span>}
                    </td>
                    <td className="px-2 py-2 text-xs text-muted">{trade.exit_reason || '—'}</td>
                    <td className="px-2 py-2 text-right font-mono">
                      {trade.r_multiple !== null ? `${trade.r_multiple.toFixed(2)}R` : '—'}
                    </td>
                    <td
                      className={`px-2 py-2 text-right font-mono ${
                        (trade.realized_pl ?? 0) >= 0 ? 'text-up' : 'text-down'
                      }`}
                    >
                      {trade.realized_pl !== null ? signedMoney(trade.realized_pl) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty>No trades recorded yet.</Empty>
        )}
      </Card>

      {stats && stats.equity_curve.length > 0 && (
        <Card title="Cumulative P&L" subtitle={`${stats.equity_curve.length} closed trades`}>
          <EquityBars points={stats.equity_curve.map((p) => p.cumulative_pnl)} />
          <div className="mt-2 flex justify-between text-xs text-muted">
            <span>{money(0)}</span>
            <span>{money(stats.equity_curve[stats.equity_curve.length - 1].cumulative_pnl)}</span>
          </div>
        </Card>
      )}
    </div>
  );
}

/** A dependency-free sparkline: one bar per closed trade. */
function EquityBars({ points }: { points: number[] }) {
  const max = Math.max(...points, 0);
  const min = Math.min(...points, 0);
  const span = max - min || 1;
  return (
    <div className="flex h-28 items-end gap-[2px]">
      {points.map((value, index) => {
        const height = ((value - min) / span) * 100;
        return (
          <div
            key={index}
            className={`flex-1 rounded-sm ${value >= 0 ? 'bg-up/70' : 'bg-down/70'}`}
            style={{ height: `${Math.max(height, 2)}%` }}
            title={`${value >= 0 ? '+' : ''}${value.toFixed(2)}`}
          />
        );
      })}
    </div>
  );
}
