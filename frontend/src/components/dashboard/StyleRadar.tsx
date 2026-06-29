'use client';
import { useEffect, useState } from 'react';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from 'recharts';
import { api } from '@/lib/api';

const card: React.CSSProperties = { background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '20px', height: '100%' };
const lbl: React.CSSProperties = { fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: '#7070a0', fontWeight: 500 };

export function StyleRadar() {
  const [data, setData] = useState<{ axis: string; value: number }[]>([]);

  useEffect(() => {
    api.getAnalyticsSummary().then((d: Record<string, unknown>) => {
      const wr = d?.win_rate != null ? Math.round(Number(d.win_rate) * 100) : 0;
      const pf = d?.profit_factor != null ? Math.min(Math.round(Number(d.profit_factor) / 3 * 100), 100) : 0;
      const exp = d?.expectancy_r != null ? Math.min(Math.max(Math.round((Number(d.expectancy_r) + 2) / 4 * 100), 0), 100) : 0;
      const dd = d?.max_drawdown_pct != null ? Math.max(100 - Math.round(Number(d.max_drawdown_pct) * 5), 0) : 0;
      const total = Number(d?.total_trades ?? 0);
      const consistency = total > 0 ? Math.min(Math.round(total / 50 * 100), 100) : 0;
      setData([
        { axis: 'Win Rate', value: wr },
        { axis: 'Profit Factor', value: pf },
        { axis: 'Expectancy', value: exp },
        { axis: 'DD Control', value: dd },
        { axis: 'Consistency', value: consistency },
      ]);
    }).catch(() => {});
  }, []);

  return (
    <div style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ ...lbl, fontSize: '11px', color: '#f0f0ff' }}>Style Radar</span>
        <span style={{ fontSize: '11px', color: '#5a5a7a' }}>LIVE DATA</span>
      </div>
      {data.length === 0 ? (
        <div style={{ color: '#5a5a7a', fontSize: '12px', padding: '40px 0', textAlign: 'center' }}>No trade data yet</div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <RadarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
            <PolarGrid stroke="rgba(255,255,255,0.08)" />
            <PolarAngleAxis dataKey="axis" tick={{ fill: '#7070a0', fontSize: 10, fontWeight: 500 }} />
            <Radar name="Style" dataKey="value" stroke="#00e5cc" fill="#00e5cc" fillOpacity={0.15} strokeWidth={2} />
          </RadarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
