'use client';

const card: React.CSSProperties = {
  background: '#0d0d22',
  border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: '12px',
  padding: '20px',
  height: '100%',
};

const label: React.CSSProperties = {
  fontSize: '10px',
  letterSpacing: '1.5px',
  textTransform: 'uppercase' as const,
  color: '#7070a0',
  fontWeight: 500,
};

const sessions = [
  { name: 'New York', pct: 0.0, wins: 0, trades: 2, color: '#7070a0' },
  { name: 'London', pct: 66.7, wins: 2, trades: 3, color: '#4a9eff' },
  { name: 'Asia', pct: 100.0, wins: 1, trades: 1, color: '#00e5a0' },
];

export function SessionWinRates() {
  return (
    <div style={card}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
        <span style={{ fontSize: '14px' }}>🕐</span>
        <span style={{ ...label, fontSize: '11px', color: '#f0f0ff' }}>Session Win Rates</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {sessions.map(s => (
          <div key={s.name}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontSize: '13px', color: '#f0f0ff', fontWeight: 500 }}>{s.name}</span>
              <span style={{ fontSize: '13px', fontWeight: 700, color: s.color, fontFamily: 'monospace' }}>
                {s.pct.toFixed(1)}%
              </span>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: '4px', height: '5px', overflow: 'hidden', marginBottom: '4px' }}>
              <div style={{ width: `${s.pct}%`, height: '100%', background: s.color, borderRadius: '4px' }} />
            </div>
            <div style={{ ...label, fontSize: '9px' }}>{s.wins} wins / {s.trades} trades</div>
          </div>
        ))}
      </div>
    </div>
  );
}
