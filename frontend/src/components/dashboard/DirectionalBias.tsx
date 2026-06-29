'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

const card: React.CSSProperties = { background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '20px' };
const lbl: React.CSSProperties = { fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase', color: '#7070a0', fontWeight: 500 };

export function DirectionalBias() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);

  useEffect(() => { api.getAnalyticsSummary().then(setData).catch(() => {}); }, []);

  const bullProfit = data?.long_pnl != null ? Number(data.long_pnl) : null;
  const bearProfit = data?.short_pnl != null ? Number(data.short_pnl) : null;
  const bullTrades = data?.long_trades != null ? Number(data.long_trades) : 0;
  const bearTrades = data?.short_trades != null ? Number(data.short_trades) : 0;

  const totalPnl = (bullProfit ?? 0) + Math.abs(bearProfit ?? 0);
  const bullPct = totalPnl > 0 ? Math.round(Math.abs(bullProfit ?? 0) / totalPnl * 100) : 50;
  const bearPct = 100 - bullPct;

  const noData = data == null || (bullTrades === 0 && bearTrades === 0);

  return (
    <div style={{ ...card, marginBottom: 0 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <span style={{ ...lbl, fontSize: '11px' }}>Tactical Decision Engine — Directional Bias</span>
        <span style={{ ...lbl, fontSize: '10px' }}>{noData ? 'NO TRADE DATA YET' : 'LIVE DATA'}</span>
      </div>

      {noData ? (
        <div style={{ textAlign: 'center', padding: '40px', color: '#5a5a7a', fontSize: '13px' }}>
          No closed trades yet. Bias will appear once trades are recorded in the journal.
        </div>
      ) : (
        <div style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
          {/* Bull */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
            <div style={{ width: 100, height: 100, borderRadius: '50%', border: '3px solid #00e5a0', boxShadow: '0 0 24px rgba(0,229,160,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,229,160,0.05)' }}>
              <span style={{ fontSize: '32px' }}>🐂</span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#00e5a0', letterSpacing: '2px' }}>BULL</div>
              <div style={{ ...lbl, marginTop: '2px' }}>LONG BIAS</div>
            </div>
            <div style={{ background: 'rgba(0,229,160,0.06)', border: '1px solid rgba(0,229,160,0.2)', borderRadius: '10px', padding: '14px', width: '100%' }}>
              <div style={{ ...lbl, marginBottom: '6px' }}>Long Trades: {bullTrades}</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#00e5a0', fontFamily: 'monospace' }}>
                {bullProfit != null ? (bullProfit >= 0 ? '+' : '') + '$' + bullProfit.toFixed(2) : '—'}{' '}
                <span style={{ fontSize: '11px', color: '#7070a0', fontFamily: 'sans-serif' }}>NET PROFIT</span>
              </div>
            </div>
          </div>

          {/* Center */}
          <div style={{ flex: '0 0 200px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
            <div style={{ fontSize: '52px', fontWeight: 800, color: '#00e5cc', fontFamily: 'monospace', lineHeight: 1 }}>{bullPct}%</div>
            <div style={{ ...lbl, color: '#00e5cc', letterSpacing: '2px' }}>LONG DOMINANCE</div>
            <div style={{ background: 'rgba(0,229,204,0.12)', border: '1px solid rgba(0,229,204,0.3)', borderRadius: '20px', padding: '6px 18px', fontSize: '12px', fontWeight: 700, color: '#00e5cc', letterSpacing: '2px' }}>VS</div>
            <div style={{ width: '100%', borderRadius: '6px', height: '10px', overflow: 'hidden', display: 'flex' }}>
              <div style={{ width: `${bullPct}%`, background: '#00e5a0' }} />
              <div style={{ width: `${bearPct}%`, background: '#ff3366' }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
              <span style={{ fontSize: '11px', color: '#00e5a0', fontWeight: 600 }}>▲ {bullPct}%</span>
              <span style={{ fontSize: '11px', color: '#ff3366', fontWeight: 600 }}>{bearPct}% ▼</span>
            </div>
          </div>

          {/* Bear */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
            <div style={{ width: 100, height: 100, borderRadius: '50%', border: '3px solid #ff3366', boxShadow: '0 0 24px rgba(255,51,102,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,51,102,0.05)' }}>
              <span style={{ fontSize: '32px' }}>🐻</span>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#ff3366', letterSpacing: '2px' }}>BEAR</div>
              <div style={{ ...lbl, marginTop: '2px' }}>SHORT BIAS</div>
            </div>
            <div style={{ background: 'rgba(255,51,102,0.06)', border: '1px solid rgba(255,51,102,0.2)', borderRadius: '10px', padding: '14px', width: '100%' }}>
              <div style={{ ...lbl, marginBottom: '6px' }}>Short Trades: {bearTrades}</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#ff3366', fontFamily: 'monospace' }}>
                {bearProfit != null ? (bearProfit >= 0 ? '+' : '') + '$' + bearProfit.toFixed(2) : '—'}{' '}
                <span style={{ fontSize: '11px', color: '#7070a0', fontFamily: 'sans-serif' }}>NET PROFIT</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
