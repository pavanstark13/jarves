'use client';
import { Card } from '@/components/ui/Card';

const DAILY_RISK_USED = 1.2; // percent
const MAX_DAILY_RISK = 3.0;

export function RiskMeter() {
  const pct = (DAILY_RISK_USED / MAX_DAILY_RISK) * 100;
  const circumference = 2 * Math.PI * 54;
  const color = pct < 50 ? '#00d4a0' : pct < 80 ? '#f5a623' : '#ff4757';

  return (
    <Card style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ marginBottom: '16px', textAlign: 'center' }}>
        <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#e8e8f0' }}>Daily Risk Meter</h2>
        <p style={{ fontSize: '12px', color: '#6b6b8a', marginTop: '2px' }}>Risk used today</p>
      </div>

      <svg width="140" height="100" viewBox="0 0 140 110">
        <path d="M 20 95 A 54 54 0 1 1 120 95" fill="none" stroke="#1e1e2e" strokeWidth="10" strokeLinecap="round" />
        <path
          d="M 20 95 A 54 54 0 1 1 120 95"
          fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference - (pct / 100) * (circumference * 0.75)}
          style={{ transition: 'stroke-dashoffset 1s ease, stroke 0.5s ease' }}
        />
        <text x="70" y="82" textAnchor="middle" fill={color} fontSize="22" fontWeight="700" fontFamily="monospace">
          {DAILY_RISK_USED}%
        </text>
        <text x="70" y="100" textAnchor="middle" fill="#6b6b8a" fontSize="11">
          of {MAX_DAILY_RISK}% limit
        </text>
      </svg>

      <div style={{ width: '100%', marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {[
          { label: 'Risk Used', value: `$${(10000 * DAILY_RISK_USED / 100).toFixed(0)}`, color: color },
          { label: 'Remaining', value: `$${(10000 * (MAX_DAILY_RISK - DAILY_RISK_USED) / 100).toFixed(0)}`, color: '#00d4a0' },
          { label: 'Open Trades', value: '2', color: '#4a9eff' },
        ].map(item => (
          <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #1e1e2e' }}>
            <span style={{ fontSize: '12px', color: '#6b6b8a' }}>{item.label}</span>
            <span style={{ fontSize: '12px', fontWeight: 600, color: item.color }}>{item.value}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
