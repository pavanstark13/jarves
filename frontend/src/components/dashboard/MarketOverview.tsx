'use client';
import { Card } from '@/components/ui/Card';
import { TrendingUp, TrendingDown } from 'lucide-react';

const MOCK_MARKETS = [
  { symbol: 'XAUUSD', name: 'Gold', price: 2318.45, change: +12.30, changePct: +0.53, trend: 'up' },
  { symbol: 'EURUSD', name: 'Euro/Dollar', price: 1.08924, change: -0.00214, changePct: -0.20, trend: 'down' },
  { symbol: 'GBPUSD', name: 'Cable', price: 1.27341, change: +0.00156, changePct: +0.12, trend: 'up' },
  { symbol: 'US30', name: 'Dow Jones', price: 37842.0, change: +118.0, changePct: +0.31, trend: 'up' },
];

function priceDisplay(symbol: string, price: number) {
  if (symbol === 'XAUUSD') return price.toFixed(2);
  if (symbol === 'US30') return price.toFixed(0);
  return price.toFixed(5);
}

export function MarketOverview() {
  return (
    <Card>
      <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#e8e8f0' }}>Market Overview</h2>
        <span style={{ fontSize: '12px', color: '#6b6b8a' }}>Live Prices</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        {MOCK_MARKETS.map((m) => (
          <div key={m.symbol} style={{
            background: '#0a0a0f', border: '1px solid #1e1e2e', borderRadius: '10px',
            padding: '14px', cursor: 'pointer', transition: 'border-color 0.2s',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#e8e8f0' }}>{m.symbol}</div>
                <div style={{ fontSize: '11px', color: '#6b6b8a' }}>{m.name}</div>
              </div>
              {m.trend === 'up'
                ? <TrendingUp size={16} color="#00d4a0" />
                : <TrendingDown size={16} color="#ff4757" />}
            </div>
            <div style={{ fontSize: '18px', fontWeight: 700, fontFamily: 'monospace', color: '#e8e8f0', marginBottom: '4px' }}>
              {priceDisplay(m.symbol, m.price)}
            </div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: m.changePct >= 0 ? '#00d4a0' : '#ff4757' }}>
              {m.changePct >= 0 ? '+' : ''}{m.changePct.toFixed(2)}%
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
