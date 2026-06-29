'use client';

interface ConfidenceScoreProps {
  score: number;
  direction: 'LONG' | 'SHORT' | 'NO_TRADE';
}

export function ConfidenceScore({ score, direction }: ConfidenceScoreProps) {
  const color = score >= 70 ? '#00d4a0' : score >= 50 ? '#f5a623' : '#ff4757';
  const dirColor = direction === 'LONG' ? '#00d4a0' : direction === 'SHORT' ? '#ff4757' : '#6b6b8a';
  const circumference = 2 * Math.PI * 60;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div style={{
      background: '#12121a', border: '1px solid #1e1e2e', borderRadius: '12px',
      padding: '24px', display: 'flex', flexDirection: 'column', alignItems: 'center',
    }}>
      <h3 style={{ fontSize: '14px', color: '#6b6b8a', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '1px' }}>Setup Quality</h3>
      <svg width="160" height="160" viewBox="0 0 160 160">
        <circle cx="80" cy="80" r="60" fill="none" stroke="#1e1e2e" strokeWidth="10" />
        <circle cx="80" cy="80" r="60" fill="none" stroke={color} strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference} strokeDashoffset={offset}
          transform="rotate(-90 80 80)"
          style={{ transition: 'stroke-dashoffset 1s ease, stroke 0.5s' }}
        />
        <text x="80" y="74" textAnchor="middle" fill={color} fontSize="32" fontWeight="700" fontFamily="monospace">{score}</text>
        <text x="80" y="94" textAnchor="middle" fill="#6b6b8a" fontSize="12">/100</text>
      </svg>
      <div style={{ marginTop: '12px', padding: '8px 24px', borderRadius: '20px', background: `${dirColor}20`, border: `1px solid ${dirColor}40`, color: dirColor, fontSize: '16px', fontWeight: 700, letterSpacing: '2px' }}>
        {direction}
      </div>
    </div>
  );
}
