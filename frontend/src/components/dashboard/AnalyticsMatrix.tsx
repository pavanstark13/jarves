'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

const label: React.CSSProperties = { fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: '#7070a0', fontWeight: 500 };

export function AnalyticsMatrix() {
  const [d, setD] = useState<Record<string, unknown> | null>(null);

  useEffect(() => { api.getAnalyticsSummary().then(setD).catch(() => {}); }, []);

  const n = (v: unknown, digits = 2) => v == null ? '—' : Number(v).toFixed(digits);
  const total   = d?.total_trades ?? '—';
  const winRate = d?.win_rate != null ? (Number(d.win_rate) * 100).toFixed(1) + '%' : '—';
  const pf      = d?.profit_factor != null ? n(d.profit_factor) : '—';
  const exp     = d?.expectancy_r != null ? (Number(d.expectancy_r) >= 0 ? '+' : '') + n(d.expectancy_r) + 'R' : '—';
  const sharpe  = d?.sharpe_ratio != null ? n(d.sharpe_ratio) : '—';
  const maxDD   = d?.max_drawdown_pct != null ? n(d.max_drawdown_pct) + '%' : '—';
  const wins    = d?.winning_trades ?? '—';
  const losses  = d?.losing_trades ?? '—';

  const metrics = [
    { label: 'WIN RATE',      value: winRate,         sub: `${total} trades`,          color: '#f0f0ff' },
    { label: 'PROFIT FACTOR', value: pf,              sub: pf !== '—' && Number(pf) > 2 ? 'Strong' : 'Moderate', color: '#f0f0ff' },
    { label: 'MAX DRAWDOWN',  value: maxDD,           sub: 'peak to trough',           color: '#ff4466' },
    { label: 'EXPECTANCY',    value: exp,             sub: 'per trade',                color: '#00d4a0' },
    { label: 'SHARPE',        value: sharpe,          sub: sharpe !== '—' && Number(sharpe) > 1 ? 'Good' : 'Low', color: '#00e5cc', large: true },
    { label: 'WINS / LOSSES', value: `${wins} / ${losses}`, sub: 'closed trades',     color: '#f0f0ff' },
    { label: 'BREAKEVEN',     value: String(d?.breakeven_trades ?? '—'), sub: 'trades', color: '#f0f0ff' },
  ];

  return (
    <div style={{ background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '16px 20px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)' }}>
        {metrics.map((m, i) => (
          <div key={m.label} style={{ padding: '12px 16px', borderRight: i < metrics.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none', background: m.large ? 'rgba(0,229,204,0.04)' : 'transparent' }}>
            <div style={label}>{m.label}</div>
            <div style={{ fontSize: m.large ? '28px' : '22px', fontWeight: 700, color: m.color, fontFamily: 'monospace', marginTop: '6px' }}>{m.value}</div>
            <div style={{ fontSize: '10px', color: '#5a5a7a', marginTop: '4px' }}>{m.sub}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
