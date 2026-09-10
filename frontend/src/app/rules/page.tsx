'use client';

import { useEffect, useState } from 'react';
import { api, ApiError } from '@/lib/api';
import { Card, Empty } from '@/components/ui';
import { dateTimeOf } from '@/lib/utils';
import type { AgentConfig, CalendarView } from '@/types';

/** The operating limits in force, read from the running agent. */
export default function RulesPage() {
  const [config, setConfig] = useState<AgentConfig | null>(null);
  const [calendar, setCalendar] = useState<CalendarView | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        setConfig(await api.config());
        setCalendar(await api.calendar(72));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : String(err));
      }
    })();
  }, []);

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <header>
        <h1 className="text-xl font-semibold">Rules</h1>
        <p className="text-sm text-muted">
          The limits the agent is running under right now. Change them in backend/.env and restart.
        </p>
      </header>

      {error && (
        <div className="rounded-lg border border-down/40 bg-down/10 px-4 py-3 text-sm text-down">{error}</div>
      )}

      <Card title="How a trade is decided">
        <ol className="space-y-2 text-sm text-muted">
          {[
            ['Regime', 'H4 EMA50 and EMA200 stacked and sloping — this sets the only direction the agent will trade.'],
            ['Daily alignment', 'The D1 EMA20 slope must not oppose that direction.'],
            ['Bias', 'H1 EMA20/EMA50 stacked the same way, price on the right side of the EMA50.'],
            ['Structure', 'M15 swings still making higher highs and higher lows (or the mirror), or a confirmed break of structure.'],
            ['Pullback', 'Price traded back to the M15 EMA20 or into an unfilled imbalance, and RSI reset through 50.'],
            ['Trigger', 'The last completed M15 bar closed back through the EMA20 in the trend direction.'],
            ['Volatility', 'M15 ATR inside a workable band — neither dead nor disorderly.'],
            ['Spread', 'The live spread is small in absolute terms and against ATR.'],
            ['Extension', 'Price is not stretched far from the EMA20, so entries never chase.'],
            ['Stop', 'Placed beyond the swing that would invalidate the setup, and the resulting risk fits the allowed band.'],
          ].map(([name, text]) => (
            <li key={name} className="flex gap-3">
              <span className="w-32 shrink-0 font-mono text-xs uppercase tracking-wide text-gold">{name}</span>
              <span>{text}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-xs text-muted">
          Every one must pass. A single failure means stand aside, and the failing measurement is
          recorded on the console.
        </p>
      </Card>

      {config && (
        <div className="grid gap-4 md:grid-cols-3">
          <ConfigCard title="Risk" values={config.risk} />
          <ConfigCard title="Trade" values={config.trade} />
          <ConfigCard title="Market gates" values={config.market} />
        </div>
      )}

      <Card
        title="Release blackout"
        subtitle={`Source: ${calendar?.source ?? '—'} · ${calendar?.blackout.reason ?? ''}`}
      >
        {calendar?.events.length ? (
          <ul className="max-h-72 space-y-1.5 overflow-y-auto text-sm">
            {calendar.events.slice(0, 30).map((event, index) => (
              <li key={index} className="flex items-center justify-between gap-3 border-b border-ink-line/60 py-1.5 last:border-0">
                <span className="text-muted">{event.name}</span>
                <span className="shrink-0 font-mono text-xs">{dateTimeOf(event.scheduled_at)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <Empty>No upcoming releases listed.</Empty>
        )}
      </Card>
    </div>
  );
}

function ConfigCard({ title, values }: { title: string; values: Record<string, string | number> }) {
  return (
    <Card title={title}>
      <dl className="space-y-1.5 text-sm">
        {Object.entries(values).map(([key, value]) => (
          <div key={key} className="flex items-baseline justify-between gap-3">
            <dt className="text-xs text-muted">{key.replace(/_/g, ' ')}</dt>
            <dd className="font-mono text-xs text-paper">{String(value)}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
