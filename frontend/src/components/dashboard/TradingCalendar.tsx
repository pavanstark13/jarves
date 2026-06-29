'use client';
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

const card: React.CSSProperties = { background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '20px' };
const lbl: React.CSSProperties = { fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: '#7070a0', fontWeight: 500 };
const DAYS = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];

export function TradingCalendar() {
  const [hovered, setHovered] = useState<number | null>(null);
  const [tradeDays, setTradeDays] = useState<Record<number, { pnl: number; trades: number }>>({});

  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const monthName = now.toLocaleString('default', { month: 'long' });
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  // getDay() is 0=Sun..6=Sat; convert to Mon-based (0=Mon..6=Sun)
  const startDow = (new Date(year, month, 1).getDay() + 6) % 7;
  const today = now.getDate();

  useEffect(() => {
    api.getTrades().then((trades: import('@/types/trade').Trade[]) => {
      const map: Record<number, { pnl: number; trades: number }> = {};
      trades.forEach(t => {
        if (!t.created_at) return;
        const d = new Date(t.created_at);
        if (d.getFullYear() !== year || d.getMonth() !== month) return;
        const day = d.getDate();
        if (!map[day]) map[day] = { pnl: 0, trades: 0 };
        map[day].pnl += t.pnl ?? 0;
        map[day].trades += 1;
      });
      setTradeDays(map);
    }).catch(() => {});
  }, [month, year]);

  const cells: (number | null)[] = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);

  return (
    <div style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <span style={{ ...lbl, fontSize: '11px', color: '#f0f0ff' }}>Trading Calendar</span>
        <span style={{ fontSize: '12px', fontWeight: 600, color: '#7070a0' }}>{monthName} {year}</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', marginBottom: '6px' }}>
        {DAYS.map(d => <div key={d} style={{ ...lbl, fontSize: '9px', textAlign: 'center' }}>{d}</div>)}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px' }}>
        {cells.map((day, i) => {
          if (day === null) return <div key={`e${i}`} />;
          const td = tradeDays[day];
          const hasTrade = td && td.trades > 0;
          const isToday = day === today;
          const isHovered = hovered === day;
          return (
            <div key={day} onMouseEnter={() => setHovered(day)} onMouseLeave={() => setHovered(null)}
              style={{ borderRadius: '6px', padding: '6px 4px', textAlign: 'center', cursor: hasTrade ? 'pointer' : 'default',
                background: isHovered && hasTrade ? 'rgba(255,255,255,0.06)' : 'transparent',
                border: isToday ? '1px solid rgba(0,229,204,0.4)' : '1px solid transparent',
                minHeight: '52px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
              <span style={{ fontSize: '12px', fontWeight: isToday ? 700 : 400, color: isToday ? '#00e5cc' : '#f0f0ff' }}>{day}</span>
              {hasTrade && td && (
                <>
                  <span style={{ fontSize: '9px', fontWeight: 700, fontFamily: 'monospace', color: td.pnl >= 0 ? '#00d4a0' : '#ff4466' }}>
                    {td.pnl >= 0 ? '+' : ''}{td.pnl.toFixed(0)}
                  </span>
                  <div style={{ width: '20px', height: '3px', borderRadius: '2px', background: td.pnl >= 0 ? '#00d4a0' : '#ff4466' }} />
                  {isHovered && <span style={{ ...lbl, fontSize: '8px' }}>{td.trades} trade{td.trades > 1 ? 's' : ''}</span>}
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
