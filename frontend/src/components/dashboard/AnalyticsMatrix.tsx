'use client';

const label: React.CSSProperties = {
  fontSize: '10px',
  letterSpacing: '1.5px',
  textTransform: 'uppercase' as const,
  color: '#7070a0',
  fontWeight: 500,
};

const bigNum: React.CSSProperties = {
  fontSize: '24px',
  fontWeight: 700,
  color: '#f0f0ff',
  fontFamily: 'monospace',
};

const metrics = [
  { label: 'WIN RATE',         value: '66.67%',    sub: '3 trades',     color: '#f0f0ff' },
  { label: 'PROFIT FACTOR',    value: '7.62',      sub: 'Strong',       color: '#f0f0ff' },
  { label: 'RECOVERY FACTOR',  value: '6.62',      sub: 'Excellent',    color: '#f0f0ff' },
  { label: 'EXPECTANCY',       value: '+$274.25',  sub: 'per trade',    color: '#00d4a0' },
  { label: 'SHARPE',           value: '9.40',      sub: 'Excellent',    color: '#00e5cc', large: true },
  { label: 'AVG HOLD',         value: '55m',       sub: '1.0 lots',     color: '#f0f0ff' },
  { label: 'ACTIVE SINCE',     value: '4d 18h 36m',sub: 'since Jun 24', color: '#f0f0ff' },
];

export function AnalyticsMatrix() {
  return (
    <div style={{
      background: '#0d0d22',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '12px',
      padding: '16px 20px',
    }}>
      <div style={{ ...label, fontSize: '11px', color: '#f0f0ff', marginBottom: '16px' }}>Analytics Matrix</div>

      <div style={{ display: 'flex', alignItems: 'stretch' }}>
        {metrics.map((m, i) => (
          <div key={m.label} style={{ display: 'flex', alignItems: 'stretch' }}>
            {i > 0 && (
              <div style={{ width: '1px', background: 'rgba(255,255,255,0.06)', margin: '0 16px', alignSelf: 'stretch' }} />
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, minWidth: 0 }}>
              <div style={label}>{m.label}</div>
              <div style={{
                ...bigNum,
                color: m.color,
                fontSize: m.large ? '32px' : '22px',
              }}>{m.value}</div>
              <div style={{ ...label, fontSize: '9px', color: '#4a4a6a' }}>{m.sub}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
