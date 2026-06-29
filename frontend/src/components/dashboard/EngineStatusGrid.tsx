'use client';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { EngineResult } from '@/types/analysis';

const MOCK_ENGINES: EngineResult[] = [
  { engine_name: 'Market Structure', signal: 'BULLISH', confidence: 0.82, details: { trend: 'uptrend', last_mss: 'H1' }, weight: 0.20 },
  { engine_name: 'Order Blocks', signal: 'DETECTED', confidence: 0.76, details: { nearest_ob: '2310.00', type: 'demand' }, weight: 0.18 },
  { engine_name: 'Fair Value Gaps', signal: 'ACTIVE', confidence: 0.68, details: { fvg_level: '2312.50' }, weight: 0.15 },
  { engine_name: 'Liquidity Map', signal: 'BULLISH', confidence: 0.71, details: { liquidity_above: '2330.00' }, weight: 0.17 },
  { engine_name: 'Session Profile', signal: 'NEUTRAL', confidence: 0.50, details: { session: 'OVERLAP' }, weight: 0.10 },
  { engine_name: 'Fibonacci', signal: 'BULLISH', confidence: 0.78, details: { level: '0.618', price: '2311.20' }, weight: 0.10 },
  { engine_name: 'RSI Momentum', signal: 'NEUTRAL', confidence: 0.55, details: { rsi: 52.4 }, weight: 0.10 },
];

function signalVariant(signal: string): 'green' | 'red' | 'blue' | 'neutral' {
  if (['BULLISH', 'DETECTED', 'ACTIVE'].includes(signal)) return 'green';
  if (signal === 'BEARISH') return 'red';
  if (signal === 'CLEAR') return 'blue';
  return 'neutral';
}

export function EngineStatusGrid() {
  return (
    <Card>
      <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#e8e8f0' }}>Engine Signals</h2>
        <span style={{ fontSize: '12px', color: '#6b6b8a' }}>XAUUSD H1</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {MOCK_ENGINES.map((e) => (
          <div key={e.engine_name} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: '#0a0a0f', border: '1px solid #1e1e2e', borderRadius: '8px', padding: '10px 14px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
              <span style={{ fontSize: '13px', color: '#e8e8f0', minWidth: '130px' }}>{e.engine_name}</span>
              <div style={{ flex: 1, height: '4px', background: '#1e1e2e', borderRadius: '2px', maxWidth: '80px' }}>
                <div style={{ height: '100%', width: `${e.confidence * 100}%`, background: signalVariant(e.signal) === 'green' ? '#00d4a0' : signalVariant(e.signal) === 'red' ? '#ff4757' : '#6b6b8a', borderRadius: '2px' }} />
              </div>
              <span style={{ fontSize: '11px', color: '#6b6b8a', minWidth: '32px' }}>{Math.round(e.confidence * 100)}%</span>
            </div>
            <Badge variant={signalVariant(e.signal)}>{e.signal}</Badge>
          </div>
        ))}
      </div>
    </Card>
  );
}
