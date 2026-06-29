'use client';
import { useState } from 'react';

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

// Mock trade data for June 2026
const tradeDays: Record<number, { pnl: number; trades: number }> = {
  24: { pnl: 423.50, trades: 1 },
  25: { pnl: 350.85, trades: 2 },
  26: { pnl: -120.00, trades: 1 },
  27: { pnl: 613.00, trades: 2 },
  28: { pnl: 0, trades: 0 },
  29: { pnl: 0, trades: 0 },
};

const DAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

// June 2026 starts on Monday (day index 0)
const JUNE_START_DOW = 0; // Monday
const JUNE_DAYS = 30;

export function TradingCalendar() {
  const [hovered, setHovered] = useState<number | null>(null);

  const cells: (number | null)[] = [];
  for (let i = 0; i < JUNE_START_DOW; i++) cells.push(null);
  for (let d = 1; d <= JUNE_DAYS; d++) cells.push(d);
  // Pad to complete last row
  while (cells.length % 7 !== 0) cells.push(null);

  return (
    <div style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <span style={{ ...label, fontSize: '11px', color: '#f0f0ff' }}>Trading Calendar</span>
        <span style={{ fontSize: '12px', fontWeight: 600, color: '#7070a0' }}>June 2026</span>
      </div>

      {/* Day headers */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', marginBottom: '6px' }}>
        {DAYS.map(d => (
          <div key={d} style={{ ...label, fontSize: '9px', textAlign: 'center' }}>{d}</div>
        ))}
      </div>

      {/* Calendar grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px' }}>
        {cells.map((day, i) => {
          if (day === null) return <div key={`empty-${i}`} />;
          const td = tradeDays[day];
          const hasTrade = td && td.trades > 0;
          const isHovered = hovered === day;

          return (
            <div
              key={day}
              onMouseEnter={() => setHovered(day)}
              onMouseLeave={() => setHovered(null)}
              style={{
                borderRadius: '6px',
                padding: '6px 4px',
                textAlign: 'center',
                cursor: hasTrade ? 'pointer' : 'default',
                background: isHovered && hasTrade ? 'rgba(255,255,255,0.06)' : 'transparent',
                border: day === 29 ? '1px solid rgba(0,229,204,0.4)' : '1px solid transparent',
                transition: 'background 0.15s',
                minHeight: '52px',
                display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px',
              }}
            >
              <span style={{
                fontSize: '12px', fontWeight: day === 29 ? 700 : 400,
                color: day === 29 ? '#00e5cc' : '#f0f0ff',
              }}>{day}</span>

              {hasTrade && td && (
                <>
                  <span style={{
                    fontSize: '9px', fontWeight: 700, fontFamily: 'monospace',
                    color: td.pnl >= 0 ? '#00d4a0' : '#ff4466',
                  }}>
                    {td.pnl >= 0 ? '+' : ''}{td.pnl.toFixed(0)}
                  </span>
                  <div style={{
                    width: '20px', height: '3px', borderRadius: '2px',
                    background: td.pnl >= 0 ? '#00d4a0' : '#ff4466',
                  }} />
                  {isHovered && (
                    <span style={{ ...label, fontSize: '8px' }}>{td.trades} trade{td.trades > 1 ? 's' : ''}</span>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
