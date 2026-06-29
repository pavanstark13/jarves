'use client';
import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { Trade } from '@/types/trade';

const MOCK_TRADES: Trade[] = [
  { id: '1', symbol: 'XAUUSD', direction: 'LONG', entry_price: 2341.20, stop_loss: 2329.00, take_profit: 2365.00, position_size: 0.05, status: 'CLOSED', entry_time: '2026-06-27T09:15:00Z', exit_time: '2026-06-27T14:30:00Z', exit_price: 2363.50, pnl: 111.50, r_multiple: 1.85, setup_quality: 82, confidence_score: 0.82, trade_direction: 'LONG', session: 'London' },
  { id: '2', symbol: 'EURUSD', direction: 'SHORT', entry_price: 1.09120, stop_loss: 1.09380, take_profit: 1.08340, position_size: 0.10, status: 'CLOSED', entry_time: '2026-06-26T14:00:00Z', exit_time: '2026-06-26T16:45:00Z', exit_price: 1.08920, pnl: 200.00, r_multiple: 0.77, setup_quality: 71, confidence_score: 0.71, trade_direction: 'SHORT', session: 'NY' },
  { id: '3', symbol: 'GBPUSD', direction: 'LONG', entry_price: 1.26840, stop_loss: 1.26480, take_profit: 1.27920, position_size: 0.08, status: 'CLOSED', entry_time: '2026-06-25T08:30:00Z', exit_time: '2026-06-25T13:00:00Z', exit_price: 1.26600, pnl: -192.00, r_multiple: -0.67, setup_quality: 68, confidence_score: 0.68, trade_direction: 'LONG', session: 'London' },
  { id: '4', symbol: 'XAUUSD', direction: 'LONG', entry_price: 2374.50, stop_loss: 2362.00, take_profit: 2409.50, position_size: 0.05, status: 'OPEN', entry_time: '2026-06-29T10:30:00Z', pnl: 64.75, setup_quality: 87, confidence_score: 0.87, trade_direction: 'LONG', session: 'NY' },
];

interface Props { trades?: Trade[]; }

export function TradeTable({ trades = MOCK_TRADES }: Props) {
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
                <td style={{ padding: '12px 14px' }}><Badge variant={t.direction === 'LONG' ? 'bull' : 'bear'}>{t.direction}</Badge></td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#e8e8f0' }}>{t.symbol === 'XAUUSD' || t.symbol === 'US30' ? t.entry_price.toFixed(2) : t.entry_price.toFixed(5)}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: t.exit_price ? '#e8e8f0' : '#6b6b8a' }}>{t.exit_price ? (t.symbol === 'XAUUSD' || t.symbol === 'US30' ? t.exit_price.toFixed(2) : t.exit_price.toFixed(5)) : '—'}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#ff4757' }}>{t.symbol === 'XAUUSD' || t.symbol === 'US30' ? t.stop_loss.toFixed(2) : t.stop_loss.toFixed(5)}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#00d4a0' }}>{t.symbol === 'XAUUSD' || t.symbol === 'US30' ? t.take_profit.toFixed(2) : t.take_profit.toFixed(5)}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: '#e8e8f0' }}>{t.position_size}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', fontWeight: 600, color: t.pnl !== undefined ? (t.pnl >= 0 ? '#00d4a0' : '#ff4757') : '#6b6b8a' }}>{t.pnl !== undefined ? `${t.pnl >= 0 ? '+' : ''}$${t.pnl.toFixed(2)}` : '—'}</td>
                <td style={{ padding: '12px 14px', fontFamily: 'monospace', color: t.r_multiple !== undefined ? (t.r_multiple >= 0 ? '#00d4a0' : '#ff4757') : '#6b6b8a' }}>{t.r_multiple !== undefined ? `${t.r_multiple >= 0 ? '+' : ''}${t.r_multiple.toFixed(1)}R` : '—'}</td>
                <td style={{ padding: '12px 14px' }}><Badge variant="info">{t.session}</Badge></td>
                <td style={{ padding: '12px 14px' }}><Badge variant={t.status === 'OPEN' ? 'bull' : t.status === 'CLOSED' ? 'neutral' : 'bear'}>{t.status}</Badge></td>
                <td style={{ padding: '12px 14px', color: '#6b6b8a', fontSize: '12px', whiteSpace: 'nowrap' }}>{new Date(t.entry_time).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
