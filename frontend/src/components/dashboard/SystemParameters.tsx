'use client';

const card: React.CSSProperties = {
  background: '#0d0d22',
  border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: '12px',
  padding: '20px',
};

const label: React.CSSProperties = {
  fontSize: '10px',
  letterSpacing: '1.5px',
  textTransform: 'uppercase' as const,
  color: '#7070a0',
  fontWeight: 500,
};

const params = [
  {
    name: 'MAX DRAWDOWN',
    badge: 'SAFE', badgeColor: '#00e5a0',
    ratio: '8 / 10 %',
    detail: '$0.0k used | $0.0k left | 30 Lot $22,000.00',
  },
  {
    name: 'DAILY DRAWDOWN',
    badge: 'SAFE', badgeColor: '#00e5a0',
    ratio: '8 / 4 %',
    detail: 'No loss | 30 Lot $34,925.70',
  },
  {
    name: 'TRADING DAYS',
    badge: 'IN PROGRESS', badgeColor: '#f0c040',
    ratio: '1 / 3 days',
    detail: '2 more needed',
  },
  {
    name: 'CONSISTENCY',
    badge: '—', badgeColor: '#7070a0',
    ratio: '79.64 / 0 %',
    detail: 'Not a requirement',
  },
];

function GaugeRing({ value }: { value: number }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const dash = (value / 100) * circ;

  return (
    <div style={{ position: 'relative', width: 120, height: 120, flexShrink: 0 }}>
      <svg width={120} height={120} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={60} cy={60} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={10} />
        <circle
          cx={60} cy={60} r={r} fill="none"
          stroke="#00e5cc" strokeWidth={10}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          style={{ filter: 'drop-shadow(0 0 6px #00e5cc)' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00e5cc', fontFamily: 'monospace' }}>{value}</span>
        <span style={{ ...label, fontSize: '9px' }}>HEALTH</span>
      </div>
    </div>
  );
}

export function SystemParameters() {
  return (
    <div style={card}>
      <div style={{ ...label, fontSize: '11px', color: '#f0f0ff', marginBottom: '20px' }}>System Parameters</div>

      <div style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
        {/* Gauge */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
          <GaugeRing value={78} />
          <div style={{
            background: 'rgba(0,229,204,0.1)', border: '1px solid rgba(0,229,204,0.3)',
            borderRadius: '6px', padding: '4px 12px',
            fontSize: '11px', fontWeight: 700, color: '#00e5cc', letterSpacing: '1px',
          }}>OPTIMAL</div>
          <div style={{ ...label, fontSize: '9px' }}>$25,000.00</div>
        </div>

        {/* Parameters tree */}
        <div style={{ flex: 1, position: 'relative' }}>
          {/* Vertical center line */}
          <div style={{
            position: 'absolute', left: 0, top: '12px', bottom: '12px',
            width: '2px', background: 'rgba(255,255,255,0.08)',
          }} />

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', paddingLeft: '20px' }}>
            {params.map((p) => (
              <div key={p.name} style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', position: 'relative' }}>
                {/* Horizontal connector */}
                <div style={{
                  position: 'absolute', left: '-20px', top: '10px',
                  width: '18px', height: '1px', background: 'rgba(255,255,255,0.08)',
                }} />

                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
                    <span style={{ ...label, fontSize: '9px', color: '#f0f0ff' }}>{p.name}</span>
                    <span style={{
                      fontSize: '9px', fontWeight: 700, padding: '1px 6px', borderRadius: '4px',
                      background: `${p.badgeColor}22`, color: p.badgeColor, letterSpacing: '0.5px',
                    }}>{p.badge}</span>
                  </div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#f0f0ff', fontFamily: 'monospace', marginBottom: '2px' }}>
                    {p.ratio}
                  </div>
                  <div style={{ ...label, fontSize: '9px', color: '#4a4a6a' }}>{p.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
