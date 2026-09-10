'use client';

import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '@/lib/api';
import { Button, Card, Empty, Pill, Stat } from '@/components/ui';
import { GateList } from '@/components/GateList';
import { ago, dateTimeOf, money, pct, price, signedMoney, timeOf } from '@/lib/utils';
import type { AgentEvent, AgentStatus, CycleReport, DecisionRow } from '@/types';

const REFRESH_MS = 10_000;

export default function ConsolePage() {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [decisions, setDecisions] = useState<DecisionRow[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');

  const load = useCallback(async () => {
    try {
      const [nextStatus, nextDecisions, nextEvents] = await Promise.all([
        api.status(),
        api.decisions(25),
        api.events(15),
      ]);
      setStatus(nextStatus);
      setDecisions(nextDecisions);
      setEvents(nextEvents);
      setError('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  const act = async (fn: () => Promise<{ message?: string }>, label: string) => {
    setBusy(true);
    setNotice('');
    try {
      const result = await fn();
      setNotice(result.message ?? `${label} done`);
      await load();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const lastCycle: CycleReport | null = status?.last_cycle ?? null;
  const decision = lastCycle?.decision ?? null;
  const position = status?.positions?.[0] ?? null;
  const day = status?.day ?? null;
  const nav = status?.account?.nav ?? 0;

  return (
    <div className="mx-auto max-w-6xl space-y-4 p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Gold Agent</h1>
          <p className="text-sm text-muted">
            XAU/USD · {status?.broker ?? '—'} · {status?.venue ?? '—'} ·{' '}
            {status ? `${status.cycles} cycles, every ${status.scan_interval_seconds}s` : '—'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={status?.mode === 'live' ? 'down' : 'gold'}>
            {status?.mode === 'live' ? 'LIVE MONEY' : 'PAPER'}
          </Pill>
          <Pill tone={status?.enabled ? 'up' : 'muted'}>
            {status?.enabled ? 'Running' : 'Stopped'}
          </Pill>
          {status?.halted && <Pill tone="down">Halted</Pill>}
        </div>
      </header>

      {error && (
        <div className="rounded-lg border border-down/40 bg-down/10 px-4 py-3 text-sm text-down">
          Cannot reach the agent API: {error}
        </div>
      )}
      {status && !status.broker_configured && (
        <div className="rounded-lg border border-gold/40 bg-gold/10 px-4 py-3 text-sm text-gold">
          {status.broker === 'mt5'
            ? 'MetaTrader 5 credentials are not configured, so there is no market data. Set MT5_LOGIN, MT5_PASSWORD and MT5_SERVER in backend/.env, and make sure the terminal is running on this machine.'
            : 'OANDA credentials are not configured, so there is no market data. Set OANDA_API_KEY and OANDA_ACCOUNT_ID in backend/.env — a free practice account is enough.'}
          {' '}Paper mode still needs them: it simulates the money, not the market.
        </div>
      )}
      {status?.halted && (
        <div className="rounded-lg border border-down/40 bg-down/10 px-4 py-3 text-sm text-down">
          Trading halted: {status.halt_reason || 'risk limit reached'}
        </div>
      )}
      {notice && (
        <div className="rounded-lg border border-ink-line bg-ink-raised px-4 py-2 text-sm text-muted">
          {notice}
        </div>
      )}

      {/* Controls */}
      <Card
        title="Controls"
        subtitle={status?.session.reason}
        right={
          <span className="text-xs text-muted">
            last cycle {ago(lastCycle?.time)}
          </span>
        }
      >
        <div className="flex flex-wrap gap-2">
          {status?.enabled ? (
            <Button variant="danger" disabled={busy} onClick={() => act(api.stop, 'Stop')}>
              Stop agent
            </Button>
          ) : (
            <Button variant="primary" disabled={busy} onClick={() => act(api.start, 'Start')}>
              Start agent
            </Button>
          )}
          <Button
            disabled={busy}
            onClick={() => act(async () => {
              const report = await api.evaluate();
              return { message: report.error || report.actions.join(' · ') || 'Evaluated the market' };
            }, 'Evaluate')}
          >
            Evaluate now
          </Button>
          <Button
            variant="danger"
            disabled={busy || !position}
            onClick={() => act(async () => {
              const result = await api.flatten();
              return { message: `Closed ${result.closed} position(s)` };
            }, 'Flatten')}
          >
            Close position
          </Button>
          {status?.halted && (
            <Button disabled={busy} onClick={() => act(api.resetHalt, 'Reset')}>
              Clear halt
            </Button>
          )}
        </div>
      </Card>

      {/* Market and account */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Market" subtitle={`Quote ${timeOf(status?.quote?.time)}`}>
          <div className="grid grid-cols-2 gap-3">
            <Stat label="Mid" value={price(status?.quote?.mid)} tone="gold" />
            <Stat
              label="Spread"
              value={status?.quote ? `$${status.quote.spread.toFixed(2)}` : '—'}
              hint={status?.quote?.tradeable === false ? 'market closed' : undefined}
            />
            <Stat label="Bid" value={price(status?.quote?.bid)} />
            <Stat label="Ask" value={price(status?.quote?.ask)} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Pill tone={status?.session.can_open ? 'up' : 'muted'}>
              {status?.session.session ?? '—'}
            </Pill>
            <span className="text-xs text-muted">{status?.session.reason}</span>
          </div>
        </Card>

        <Card title="Account" subtitle={status?.account?.venue}>
          <div className="grid grid-cols-2 gap-3">
            <Stat label="NAV" value={money(status?.account?.nav)} />
            <Stat
              label="Open P&L"
              value={signedMoney(status?.account?.unrealized_pl)}
              tone={(status?.account?.unrealized_pl ?? 0) >= 0 ? 'up' : 'down'}
            />
            <Stat
              label="Today"
              value={signedMoney(day?.realized_pl)}
              tone={(day?.realized_pl ?? 0) >= 0 ? 'up' : 'down'}
              hint={day ? `${pct(day.daily_loss_pct ?? 0)} of the daily limit used` : undefined}
            />
            <Stat
              label="Drawdown"
              value={pct(day?.drawdown_pct ?? 0)}
              tone={(day?.drawdown_pct ?? 0) > 0 ? 'down' : 'neutral'}
              hint={day ? `peak ${money(day.peak_nav)}` : undefined}
            />
          </div>
          {day && (
            <p className="mt-3 text-xs text-muted">
              {day.trades_opened} trade(s) opened today · {day.consecutive_losses} loss streak
              {day.cooldown_until ? ` · cooling off until ${timeOf(day.cooldown_until)}` : ''}
            </p>
          )}
        </Card>
      </div>

      {/* Position */}
      <Card title="Open position">
        {position ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Pill tone={position.direction === 'LONG' ? 'up' : 'down'}>{position.direction}</Pill>
              <span className="font-mono text-sm">{position.units} oz</span>
              <span className="text-xs text-muted">opened {dateTimeOf(position.opened_at)}</span>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Stat label="Entry" value={price(position.entry_price)} />
              <Stat label="Stop" value={price(position.stop_loss)} tone="down" />
              <Stat label="Target" value={price(position.take_profit)} tone="up" />
              <Stat
                label="Open P&L"
                value={signedMoney(position.unrealized_pl)}
                tone={position.unrealized_pl >= 0 ? 'up' : 'down'}
                hint={`risk $${position.initial_risk.toFixed(2)}/oz`}
              />
            </div>
          </div>
        ) : (
          <Empty>Flat. The agent holds nothing right now.</Empty>
        )}
      </Card>

      {/* Latest evaluation */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card
          title="Latest evaluation"
          subtitle={decision?.summary ?? 'No evaluation recorded yet'}
          right={
            decision && (
              <Pill tone={decision.action === 'STAND_ASIDE' ? 'muted' : decision.action === 'LONG' ? 'up' : 'down'}>
                {decision.action}
              </Pill>
            )
          }
        >
          <GateList gates={decision?.gates ?? []} />
          {lastCycle?.risk && (
            <div className="mt-4 rounded-lg border border-ink-line bg-ink px-3 py-2.5">
              <div className="text-[11px] uppercase tracking-wider text-muted">Risk check</div>
              <div className={`mt-1 text-sm ${lastCycle.risk.approved ? 'text-up' : 'text-down'}`}>
                {lastCycle.risk.reason}
              </div>
            </div>
          )}
          {!!lastCycle?.actions.length && (
            <ul className="mt-3 space-y-1 text-xs text-muted">
              {lastCycle.actions.map((action, index) => (
                <li key={index}>· {action}</li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-4">
          <Card title="Decision log" subtitle="Every evaluation, taken or not">
            {decisions.length ? (
              <ul className="max-h-72 space-y-1.5 overflow-y-auto">
                {decisions.map((row) => (
                  <li
                    key={row.id}
                    className="flex items-start gap-2.5 rounded-lg border border-ink-line bg-ink px-3 py-2"
                  >
                    <span className="shrink-0 font-mono text-[11px] text-muted">
                      {timeOf(row.time)}
                    </span>
                    <span className="min-w-0 text-xs text-paper">
                      {row.executed && <span className="mr-1 text-gold">●</span>}
                      {row.blocker || row.summary}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>Nothing evaluated yet.</Empty>
            )}
          </Card>

          <Card title="Agent log">
            {events.length ? (
              <ul className="max-h-56 space-y-1.5 overflow-y-auto">
                {events.map((event) => (
                  <li key={event.id} className="flex items-start gap-2.5 text-xs">
                    <span className="shrink-0 font-mono text-[11px] text-muted">
                      {timeOf(event.time)}
                    </span>
                    <span className="shrink-0 font-mono text-[11px] uppercase text-gold">
                      {event.kind}
                    </span>
                    <span className="min-w-0 text-muted">{event.message}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>No events yet.</Empty>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
