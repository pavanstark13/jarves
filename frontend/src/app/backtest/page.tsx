'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '@/lib/api';
import { Button, Card, Empty, Pill, Stat } from '@/components/ui';
import { dateTimeOf, money, pct, price, signedMoney } from '@/lib/utils';
import type { BacktestRun } from '@/types';

export default function BacktestPage() {
  const [days, setDays] = useState(60);
  const [balance, setBalance] = useState(10_000);
  const [spread, setSpread] = useState(0.3);
  const [run, setRun] = useState<BacktestRun | null>(null);
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);
  const poller = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (poller.current) {
      clearInterval(poller.current);
      poller.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const start = async () => {
    setStarting(true);
    setError('');
    setRun(null);
    try {
      const { run_id } = await api.runBacktest({
        days,
        starting_balance: balance,
        assumed_spread: spread,
      });
      stopPolling();
      poller.current = setInterval(async () => {
        try {
          const next = await api.backtestRun(run_id);
          setRun(next);
          if (next.status !== 'RUNNING') stopPolling();
        } catch (err) {
          setError(err instanceof ApiError ? err.message : String(err));
          stopPolling();
        }
      }, 2000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setStarting(false);
    }
  };

  const result = run?.result;

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <header>
        <h1 className="text-xl font-semibold">Backtest</h1>
        <p className="text-sm text-muted">
          The live rules replayed over real OANDA gold history — the same strategy, risk and
          trade-management code the agent runs.
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-down/40 bg-down/10 px-4 py-3 text-sm text-down">{error}</div>
      )}

      <Card title="Run">
        <div className="flex flex-wrap items-end gap-4">
          <Field label="Days of history" value={days} min={5} max={365} onChange={setDays} />
          <Field label="Starting balance" value={balance} min={100} max={1_000_000} step={100} onChange={setBalance} />
          <Field label="Assumed spread ($)" value={spread} min={0} max={5} step={0.05} onChange={setSpread} />
          <Button variant="primary" disabled={starting || run?.status === 'RUNNING'} onClick={start}>
            {run?.status === 'RUNNING' ? 'Running…' : 'Run backtest'}
          </Button>
        </div>
        <p className="mt-3 text-xs text-muted">
          Requires OANDA credentials — the history is fetched from the broker. Longer windows take
          longer to page in.
        </p>
      </Card>

      {run?.status === 'FAILED' && (
        <div className="rounded-lg border border-down/40 bg-down/10 px-4 py-3 text-sm text-down">
          {run.error}
        </div>
      )}

      {result && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
            <Stat label="Trades" value={result.total_trades} />
            <Stat label="Win rate" value={pct(result.win_rate, 1)} />
            <Stat
              label="Net P&L"
              value={signedMoney(result.total_pnl)}
              tone={result.total_pnl >= 0 ? 'up' : 'down'}
            />
            <Stat label="Profit factor" value={result.profit_factor.toFixed(2)} />
            <Stat label="Expectancy" value={`${result.expectancy_r.toFixed(2)}R`} />
            <Stat label="Max drawdown" value={pct(result.max_drawdown_pct, 1)} tone="down" />
          </div>

          <Card
            title="Result"
            subtitle={`${dateTimeOf(result.start)} → ${dateTimeOf(result.end)} · ${result.bars_tested} M15 bars`}
            right={<Pill tone="muted">{money(result.starting_balance)} → {money(result.ending_balance)}</Pill>}
          >
            <p className="text-xs text-muted">{result.note}</p>
            {result.total_trades === 0 && (
              <p className="mt-3 text-sm text-muted">
                No trade passed every gate in this window. That is a valid outcome, not an error —
                the rules are built to stand aside far more often than they trade.
              </p>
            )}
          </Card>

          {!!result.trades?.length && (
            <Card title="Trades">
              <div className="max-h-96 overflow-auto">
                <table className="w-full min-w-[720px] text-sm">
                  <thead className="sticky top-0 bg-ink-raised">
                    <tr className="border-b border-ink-line text-left text-[11px] uppercase tracking-wider text-muted">
                      <th className="px-2 py-2 font-medium">Entry</th>
                      <th className="px-2 py-2 font-medium">Side</th>
                      <th className="px-2 py-2 text-right font-medium">Price</th>
                      <th className="px-2 py-2 text-right font-medium">Exit</th>
                      <th className="px-2 py-2 font-medium">Reason</th>
                      <th className="px-2 py-2 text-right font-medium">R</th>
                      <th className="px-2 py-2 text-right font-medium">P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((trade, index) => (
                      <tr key={index} className="border-b border-ink-line/60 last:border-0">
                        <td className="px-2 py-2 text-muted">{dateTimeOf(trade.entry_time)}</td>
                        <td className="px-2 py-2">
                          <Pill tone={trade.direction === 'LONG' ? 'up' : 'down'}>{trade.direction}</Pill>
                        </td>
                        <td className="px-2 py-2 text-right font-mono">{price(trade.entry_price)}</td>
                        <td className="px-2 py-2 text-right font-mono">{price(trade.exit_price)}</td>
                        <td className="px-2 py-2 text-xs text-muted">{trade.exit_reason}</td>
                        <td className="px-2 py-2 text-right font-mono">{trade.r_multiple.toFixed(2)}R</td>
                        <td
                          className={`px-2 py-2 text-right font-mono ${
                            trade.pnl >= 0 ? 'text-up' : 'text-down'
                          }`}
                        >
                          {signedMoney(trade.pnl)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}

      {!run && <Empty>Run a backtest to see how the rules behaved on real history.</Empty>}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
}) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wider text-muted">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
        className="mt-1 block w-36 rounded-lg border border-ink-line bg-ink px-3 py-1.5 font-mono text-sm text-paper outline-none focus:border-gold/50"
      />
    </label>
  );
}
