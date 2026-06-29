'use client';
import { Badge } from '@/components/ui/Badge';
import type { EngineResult as EngineResultType } from '@/types/analysis';

interface Props { engine: EngineResultType; }

function signalVariant(signal: string): 'green' | 'red' | 'blue' | 'neutral' {
  if (['BULLISH', 'DETECTED', 'ACTIVE'].includes(signal)) return 'green';
  if (signal === 'BEARISH') return 'red';
  if (signal === 'CLEAR') return 'blue';
  return 'neutral';
}

export function EngineResult({ engine }: Props) {
  const v = signalVariant(engine.signal);
  const barColor = v === 'green' ? '#00d4a0' : v === 'red' ? '#ff4757' : '#6b6b8a';

  return (
    <div style={{
      background: '#0a0a0f', border: '1px solid #1e1e2e', borderRadius: '10px',
      padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#e8e8f0' }}>{engine.engine_name}</div>
          <div style={{ fontSize: '11px', color: '#6b6b8a', marginTop: '2px' }}>Weight: {Math.round(engine.weight * 100)}%</div>
        </div>
        <Badge variant={v}>{engine.signal}</Badge>
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ fontSize: '11px', color: '#6b6b8a' }}>Confidence</span>
          <span style={{ fontSize: '11px', color: barColor, fontWeight: 600 }}>{Math.round(engine.confidence * 100)}%</span>
        </div>
        <div style={{ height: '6px', background: '#1e1e2e', borderRadius: '3px' }}>
          <div style={{ height: '100%', width: `${engine.confidence * 100}%`, background: barColor, borderRadius: '3px', transition: 'width 0.8s ease' }} />
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {Object.entries(engine.details).slice(0, 3).map(([k, v]) => (
          <div key={k} style={{ background: '#1e1e2e', borderRadius: '4px', padding: '3px 8px', fontSize: '11px' }}>
            <span style={{ color: '#6b6b8a' }}>{k}: </span>
            <span style={{ color: '#e8e8f0', fontFamily: 'monospace' }}>{String(v)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
