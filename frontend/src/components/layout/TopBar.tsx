'use client';
import { Bell, Settings, Clock } from 'lucide-react';
import { useState, useEffect } from 'react';

export function TopBar() {
  const [time, setTime] = useState('');
  useEffect(() => {
    const update = () => setTime(new Date().toUTCString().slice(17, 25) + ' UTC');
    update();
    const t = setInterval(update, 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <div style={{
      height: '56px', background: '#0d0d15', borderBottom: '1px solid #1e1e2e',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 24px', flexShrink: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#6b6b8a', fontSize: '13px' }}>
        <Clock size={14} />
        <span style={{ fontFamily: 'monospace' }}>{time}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{ padding: '8px', borderRadius: '8px', cursor: 'pointer', color: '#6b6b8a' }}><Bell size={18} /></div>
        <div style={{ padding: '8px', borderRadius: '8px', cursor: 'pointer', color: '#6b6b8a' }}><Settings size={18} /></div>
        <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'linear-gradient(135deg, #4a9eff, #00d4a0)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px', fontWeight: 700, color: '#fff' }}>J</div>
      </div>
    </div>
  );
}
