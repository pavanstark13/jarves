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

const SESSIONS = [
  { name: 'Sydney',   start: 22, end: 31, color: '#f0c040' },   // 22-07 (wraps)
  { name: 'Tokyo',    start: 0,  end: 9,  color: '#ff8c42' },
  { name: 'London',   start: 7,  end: 16, color: '#4a9eff' },
  { name: 'New York', start: 13, end: 22, color: '#00e5a0' },
];

const HOURS = [0, 6, 12, 18, 24];
const TOTAL_HOURS = 24;

function getBarStyle(start: number, end: number, color: string, currentHour: number) {
  const s = start > 24 ? start - 24 : start;
  const e = end > 24 ? end - 24 : end;

  // For Sydney which wraps midnight
  if (start >= 22 && end > 24) {
    // Two segments: 22-24 and 0-(end-24)
    return [
      { left: `${(22 / TOTAL_HOURS) * 100}%`, width: `${(2 / TOTAL_HOURS) * 100}%`, color },
      { left: `0%`, width: `${((end - 24) / TOTAL_HOURS) * 100}%`, color },
    ];
  }

  const isActive = currentHour >= s && currentHour < e;
  return [{ left: `${(s / TOTAL_HOURS) * 100}%`, width: `${((e - s) / TOTAL_HOURS) * 100}%`, color, isActive }];
}

export function MarketHours() {
  // Static time for demo
  const currentHour = 9;
  const currentMin = 42;
  const currentPct = ((currentHour + currentMin / 60) / TOTAL_HOURS) * 100;

  return (
    <div style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '14px' }}>🕐</span>
          <span style={{ ...label, fontSize: '11px', color: '#f0f0ff' }}>Market Hours</span>
        </div>
        <span style={{ fontSize: '12px', fontFamily: 'monospace', color: '#00e5cc', fontWeight: 700 }}>09:42 UTC</span>
      </div>

      {/* Hour markers */}
      <div style={{ position: 'relative', marginBottom: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          {HOURS.map(h => (
            <span key={h} style={{ ...label, fontSize: '9px' }}>{String(h).padStart(2, '0')}</span>
          ))}
        </div>
      </div>

      {/* Session rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {SESSIONS.map(s => {
          const bars = getBarStyle(s.start, s.end, s.color, currentHour);
          return (
            <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ ...label, fontSize: '9px', width: '52px', flexShrink: 0 }}>{s.name}</span>
              <div style={{ flex: 1, position: 'relative', height: '16px', background: 'rgba(255,255,255,0.04)', borderRadius: '4px', overflow: 'hidden' }}>
                {bars.map((b, i) => (
                  <div key={i} style={{
                    position: 'absolute', top: 0, bottom: 0,
                    left: b.left, width: b.width,
                    background: b.color,
                    opacity: 0.7,
                    borderRadius: '4px',
                    boxShadow: (b as any).isActive ? `0 0 8px ${b.color}` : undefined,
                  }} />
                ))}
                {/* Current time line */}
                <div style={{
                  position: 'absolute', top: 0, bottom: 0, width: '2px',
                  left: `${currentPct}%`, background: '#ffffff', opacity: 0.8,
                }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
