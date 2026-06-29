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
  textTransform: 'uppercase',
  color: '#7070a0',
  fontWeight: 500,
};

export function DirectionalBias() {
  const bullProfit = 817;
  const bearProfit = 443;
  const total = bullProfit + bearProfit;
  const bullPct = Math.round((bullProfit / total) * 100);
  const bearPct = 100 - bullPct;

  return (
    <div style={{ ...card, marginBottom: 0 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <span style={{ ...label, fontSize: '11px' }}>Tactical Decision Engine — Directional Bias</span>
        <span style={{ ...label, fontSize: '10px' }}>LATENCY: 12ms | 0.0 Data</span>
      </div>

      {/* Main 3-col layout */}
      <div style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>

        {/* LEFT: Bull */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          {/* Circle */}
          <div style={{
            width: 100, height: 100, borderRadius: '50%',
            border: '3px solid #00e5a0',
            boxShadow: '0 0 24px rgba(0,229,160,0.5), inset 0 0 24px rgba(0,229,160,0.1)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0,229,160,0.05)',
          }}>
            <span style={{ fontSize: '32px', lineHeight: 1 }}>🐂</span>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#00e5a0', letterSpacing: '2px' }}>BULL</div>
            <div style={{ ...label, color: '#7070a0', marginTop: '2px' }}>LONG BIAS</div>
          </div>

          {/* Bull Faction Card */}
          <div style={{
            background: 'rgba(0,229,160,0.06)', border: '1px solid rgba(0,229,160,0.2)',
            borderRadius: '10px', padding: '14px', width: '100%',
          }}>
            <div style={{ ...label, marginBottom: '6px' }}>Bull Faction / Long Bias</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: '#00e5a0', fontFamily: 'monospace' }}>
              +${bullProfit.toFixed(2)} <span style={{ fontSize: '11px', color: '#7070a0', fontFamily: 'sans-serif' }}>NET PROFIT</span>
            </div>
            <div style={{ ...label, marginTop: '10px', marginBottom: '4px' }}>POWER LEVEL</div>
            <div style={{ background: 'rgba(255,255,255,0.08)', borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
              <div style={{ width: '30%', height: '100%', background: '#00e5a0', borderRadius: '4px' }} />
            </div>
            <div style={{ ...label, marginTop: '4px', textAlign: 'right' }}>30/100</div>
          </div>
        </div>

        {/* CENTER */}
        <div style={{ flex: '0 0 200px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <div style={{ fontSize: '52px', fontWeight: 800, color: '#00e5cc', fontFamily: 'monospace', lineHeight: 1 }}>
            {bullPct}%
          </div>
          <div style={{ ...label, color: '#00e5cc', letterSpacing: '2px' }}>LONG DOMINANCE</div>

          <div style={{
            background: 'rgba(0,229,204,0.12)', border: '1px solid rgba(0,229,204,0.3)',
            borderRadius: '20px', padding: '6px 18px', fontSize: '12px', fontWeight: 700,
            color: '#00e5cc', letterSpacing: '2px', cursor: 'pointer',
          }}>VS</div>

          {/* Split bar */}
          <div style={{ width: '100%', borderRadius: '6px', height: '10px', overflow: 'hidden', display: 'flex' }}>
            <div style={{ width: `${bullPct}%`, background: '#00e5a0' }} />
            <div style={{ width: `${bearPct}%`, background: '#ff3366' }} />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
            <span style={{ fontSize: '11px', color: '#00e5a0', fontWeight: 600 }}>▲ {bullPct}%</span>
            <span style={{ fontSize: '11px', color: '#ff3366', fontWeight: 600 }}>{bearPct}% ▼</span>
          </div>
        </div>

        {/* RIGHT: Bear */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          {/* Circle */}
          <div style={{
            width: 100, height: 100, borderRadius: '50%',
            border: '3px solid #ff3366',
            boxShadow: '0 0 24px rgba(255,51,102,0.5), inset 0 0 24px rgba(255,51,102,0.1)',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(255,51,102,0.05)',
          }}>
            <span style={{ fontSize: '32px', lineHeight: 1 }}>🐻</span>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#ff3366', letterSpacing: '2px' }}>BEAR</div>
            <div style={{ ...label, color: '#7070a0', marginTop: '2px' }}>SHORT BIAS</div>
          </div>

          {/* Bear Faction Card */}
          <div style={{
            background: 'rgba(255,51,102,0.06)', border: '1px solid rgba(255,51,102,0.2)',
            borderRadius: '10px', padding: '14px', width: '100%',
          }}>
            <div style={{ ...label, marginBottom: '6px' }}>Bear Faction / Short Bias</div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: '#ff3366', fontFamily: 'monospace' }}>
              +${bearProfit.toFixed(2)} <span style={{ fontSize: '11px', color: '#7070a0', fontFamily: 'sans-serif' }}>NET PROFIT</span>
            </div>
            <div style={{ ...label, marginTop: '10px', marginBottom: '4px' }}>POWER LEVEL</div>
            <div style={{ background: 'rgba(255,255,255,0.08)', borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
              <div style={{ width: '30%', height: '100%', background: '#ff3366', borderRadius: '4px' }} />
            </div>
            <div style={{ ...label, marginTop: '4px', textAlign: 'right' }}>30/100</div>
          </div>
        </div>

      </div>
    </div>
  );
}
