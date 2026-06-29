'use client';

const label: React.CSSProperties = {
  fontSize: '10px',
  letterSpacing: '1.5px',
  textTransform: 'uppercase' as const,
  color: '#7070a0',
  fontWeight: 500,
};

export function ProfitTarget() {
  const current = 1267.35;
  const target = 2000.00;
  const pct = (current / target) * 100;
  const left = target - current;

  return (
    <div style={{
      background: '#0d0d22',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: '12px',
      padding: '20px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <span style={{ ...label, fontSize: '11px', color: '#f0f0ff' }}>Profit Target</span>
        <span style={{ fontSize: '12px', fontWeight: 700, color: '#00e5cc', fontFamily: 'monospace' }}>
          {pct.toFixed(1)}% TARGET
        </span>
      </div>

      {/* Progress bar */}
      <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: '6px', height: '12px', overflow: 'hidden', marginBottom: '10px' }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: 'linear-gradient(90deg, #00b8a0, #00e5cc)',
          borderRadius: '6px',
          boxShadow: '0 0 12px rgba(0,229,204,0.4)',
          transition: 'width 0.5s ease',
        }} />
      </div>

      {/* Values row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontSize: '16px', fontWeight: 700, color: '#00e5cc', fontFamily: 'monospace' }}>
            ${current.toFixed(2)}
          </span>
          <span style={{ fontSize: '14px', color: '#7070a0', fontFamily: 'monospace' }}>
            {' '}/ ${target.toFixed(2)}
          </span>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ ...label }}>REMAINING</div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: '#ff4466', fontFamily: 'monospace' }}>
            ${left.toFixed(2)} LEFT
          </div>
        </div>
      </div>
    </div>
  );
}
