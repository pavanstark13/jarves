'use client';

import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from 'recharts';

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

const data = [
  { axis: 'SL Usage', value: 60 },
  { axis: 'TP Usage', value: 80 },
  { axis: 'Win Rate', value: 67 },
  { axis: 'Risk/Reward', value: 75 },
  { axis: 'Pass Rate', value: 70 },
];

export function StyleRadar() {
  return (
    <div style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <span style={{ ...label, fontSize: '11px', color: '#f0f0ff' }}>Style Radar</span>
        <span style={{ fontSize: '14px', cursor: 'pointer', color: '#7070a0' }}>✏️</span>
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <RadarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
          <PolarGrid stroke="rgba(255,255,255,0.08)" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fill: '#7070a0', fontSize: 10, fontWeight: 500 }}
          />
          <Radar
            name="Style"
            dataKey="value"
            stroke="#00e5cc"
            fill="#00e5cc"
            fillOpacity={0.15}
            strokeWidth={2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
