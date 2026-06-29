'use client';
import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { Trade } from '@/types/trade';

interface Props { trades: Trade[]; }

export function TradeTable({ trades }: Props) {
  const [filter, setFilter] = useState<'ALL' | 'OPEN' | 'CLOSED'>('ALL');
  const [symbolFilter, setSymbolFilter] = useState('ALL');

  const symbols = ['ALL', ...Array.from(new Set(trades.map(t => t.symbol)))];
  const filtered = trades.filter(t =>
    (filter === 'ALL' || t.status === filter) &&
    (symbolFilter === 'ALL' || t.symbol === symbolFilter)
  );

  const selectStyle = {
    background: '#0a0a0f', border: '1px solid #1e1e2e', color: '#e8e8f0',
    borderRadius: '6px', padding: '6px 10px', fontSize: '12px', cursor: 'pointer',
  };

  return (
    <Card style={{ padding: 0 }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #1e1e2e', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#e8e8f0', flex: 1 }}>Trade History</h2>
        <select value={symbolFilter} onChange={e => setSymbolFilter(e.target.value)} style={selectStyle}>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <div style={{ display: 'flex', gap: '4px' }}>
          {(['ALL', 'OPEN', 'CLOSED'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '6px 12px', borderRadius: '6px', fontSize: '12px', fontWeight: 500, cursor: 'pointer',
              background: filter === f ? '#4a9eff' : 'transparent',
              color: filter === f ? '#fff' : '#6b6b8a',
              border: filter === f ? '1px solid #4a9eff' : '1px solid #1e1e2e',
            }}>{f}</button>
          ))}
        </div>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ background: '#0a0a0f' }}>
              {['Symbol', 'Dir', 'Entry', 'Exit', 'SL', 'TP', 'Size', 'P&L', 'R', 'Session', 'Status', 'Date'].map(h => (
                <th key={h} style={{ padding: '10px 14px', textAlign: 'left', color: '#6b6b8a', fontSize: '11px', fontWeight: 500, whiteSpace: 'nowrap', borderBottom: '1px solid #1e1e2e' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(t => (
              <tr key={t.id} style={{ borderBottom: '1px solid #1e1e2e' }}>
                <td style={{ padding: '12px 14px', fontWeight: 600, color: '#e8e8f0' }}>{t.symbol}</td>
                <td style={{ padding: '12px 14px' }}><Badge variant={t.direction === 'LONG' ? 'green' : 'red'}>{t.direction}</Badge></td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#e8e8f0' }}>{t.symbol === 'XAUUSD' || t.symbol === 'US30' ? t.entry_price.toFixed(2) : t.entry_price.toFixed(5)}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: t.exit_price ? '#e8e8f0' : '#6b6b8a' }}>{t.exit_price ? (t.symbol === 'XAUUSD' || t.symbol === 'US30' ? t.exit_price.toFixed(2) : t.exit_price.toFixed(5)) : '—'}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#ff4757' }}>{t.symbol === 'XAUUSD' || t.symbol === 'US30' ? t.stop_loss.toFixed(2) : t.stop_loss.toFixed(5)}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#00d4a0' }}>{t.symbol === 'XAUUSD' || t.symbol === 'US30' ? t.take_profit.toFixed(2) : t.take_profit.toFixed(5)}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#e8e8f0' }}>{t.position_size}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', fontWeight: 600, color: t.pnl !== undefined ? (t.pnl >= 0 ? '#00d4a0' : '#ff4757') : '#6b6b8a' }}>{t.pnl !== undefined ? `${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)}` : '—'}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: t.pnl_r !== undefined ? (t.pnl_r >= 0 ? '#00d4a0' : '#ff4757') : '#6b6b8a' }}>{t.pnl_r !== undefined ? `${t.pnl_r >= 0 ? '+' : ''}${t.pnl_r.toFixed(1)}R` : '—'}</td>
                <td style={{ padding: '12px 14px' }}><Badge variant="blue">{t.session}</Badge></td>
                <td style={{ padding: '12px 14px' }}><Badge variant={t.status === 'OPEN' ? 'green' : t.status === 'CLOSED' ? 'neutral' : 'red'}>{t.status}</Badge></td>
                <td style={{ padding: '12px 14px', color: '#6b6b8a', fontSize: '12px', whiteSpace: 'nowrap' }}>{new Date(t.entry_time).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
