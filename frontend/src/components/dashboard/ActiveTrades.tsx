'use client';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

const MOCK_ACTIVE = [
  { id: '3', symbol: 'GBPUSD', direction: 'LONG', entry: 1.27340, current: 1.27510, sl: 1.27100, tp: 1.27900, size: 0.5, pnl: +85.0, pnlPct: +0.134 },
  { id: '6', symbol: 'XAUUSD', direction: 'LONG', entry: 2318.50, current: 2322.80, sl: 2310.00, tp: 2345.00, size: 0.1, pnl: +43.0, pnlPct: +0.185 },
];

export function ActiveTrades() {
  return (
    <Card>
      <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#e8e8f0' }}>Active Positions</h2>
        <span style={{ fontSize: '12px', color: '#6b6b8a' }}>{MOCK_ACTIVE.length} open</span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr>
              {['Symbol', 'Dir', 'Entry', 'Current', 'SL', 'TP', 'Size', 'P&L'].map(h => (
                <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#6b6b8a', fontSize: '11px', fontWeight: 500, borderBottom: '1px solid #1e1e2e', whiteSpace: 'nowrap' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MOCK_ACTIVE.map((t) => (
              <tr key={t.id} style={{ borderBottom: '1px solid #1e1e2e' }}>
                <td style={{ padding: '12px', fontWeight: 600, color: '#e8e8f0' }}>{t.symbol}</td>
                <td style={{ padding: '12px' }}>
                  <Badge variant={t.direction === 'LONG' ? 'green' : 'red'}>{t.direction}</Badge>
                </td>
                <td style={{ padding: '12px', fontFamily: 'monospace', color: '#e8e8f0' }}>{t.symbol === 'XAUUSD' ? t.entry.toFixed(2) : t.entry.toFixed(5)}</td>
                <td style={{ padding: '12px', fontFamily: 'monospace', color: '#e8e8f0' }}>{t.symbol === 'XAUUSD' ? t.current.toFixed(2) : t.current.toFixed(5)}</td>
                <td style={{ padding: '12px', fontFamily: 'monospace', color: '#ff4757' }}>{t.symbol === 'XAUUSD' ? t.sl.toFixed(2) : t.sl.toFixed(5)}</td>
                <td style={{ padding: '12px', fontFamily: 'monospace', color: '#00d4a0' }}>{t.symbol === 'XAUUSD' ? t.tp.toFixed(2) : t.tp.toFixed(5)}</td>
                <td style={{ padding: '12px', fontFamily: 'monospace', color: '#e8e8f0' }}>{t.size}</td>
                <td style={{ padding: '12px', fontFamily: 'monospace', fontWeight: 600, color: t.pnl >= 0 ? '#00d4a0' : '#ff4757' }}>
                  {t.pnl >= 0 ? '+' : ''}${t.pnl.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
