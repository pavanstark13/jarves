'use client';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

const card: React.CSSProperties = { background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '20px', height: '100%' };
const lbl: React.CSSProperties = { fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: '#7070a0', fontWeight: 500 };

const SESSION_COLORS: Record<string, string> = { LONDON: '#4a9eff', NEW_YORK: '#7070a0', OVERLAP: '#00e5cc', ASIA: '#00e5a0', KILL_ZONE: '#f5a623' };
const SESSION_LABELS: Record<string, string> = { LONDON: 'London', NEW_YORK: 'New York', OVERLAP: 'Overlap', ASIA: 'Asia', KILL_ZONE: 'Kill Zone' };

export function SessionWinRates() {
  const [sessions, setSessions] = useState<{ name: string; pct: number; wins: number; trades: number; color: string }[]>([]);
  const [empty, setEmpty] = useState(false);

  useEffect(() => {
    api.getAnalyticsSummary().then((d: Record<string, unknown>) => {
      const raw = d?.session_stats as Record<string, { total: number; win_rate: number }> | null;
      if (!raw || Object.keys(raw).length === 0) { setEmpty(true); return; }
      const rows = Object.entries(raw).map(([k, v]) => ({
        name: SESSION_LABELS[k] ?? k,
        pct: Math.round(v.win_rate * 100),
        wins: Math.round(v.win_rate * v.total),
        trades: v.total,
        color: SESSION_COLORS[k] ?? '#7070a0',
      }));
      setSessions(rows);
    }).catch(() => setEmpty(true));
  }, []);

  return (
    <div style={card}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
        <span style={{ fontSize: '14px' }}>🕐</span>
        <span style={{ ...lbl, fontSize: '11px', color: '#f0f0ff' }}>Session Win Rates</span>
      </div>

      {empty || sessions.length === 0 ? (
        <div style={{ color: '#5a5a7a', fontSize: '12px', padding: '20px 0' }}>No session data yet. Trade records will populate this once trades are closed.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {sessions.map(s => (
            <div key={s.name}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '13px', color: '#f0f0ff', fontWeight: 500 }}>{s.name}</span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: s.color, fontFamily: 'monospace' }}>{s.pct}%</span>
              </div>
              <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: '4px', height: '5px', overflow: 'hidden', marginBottom: '4px' }}>
                <div style={{ width: `${s.pct}%`, height: '100%', background: s.color, borderRadius: '4px' }} />
              </div>
              <div style={{ ...lbl, fontSize: '9px' }}>{s.wins} wins / {s.trades} trades</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
