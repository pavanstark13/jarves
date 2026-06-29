type Variant = 'green' | 'bull' | 'red' | 'bear' | 'blue' | 'info' | 'neutral';

interface BadgeProps {
  children: React.ReactNode;
  variant?: Variant;
}

const colors: Record<Variant, { bg: string; color: string; border: string }> = {
  green: { bg: 'rgba(0,212,160,0.15)', color: '#00d4a0', border: 'rgba(0,212,160,0.3)' },
  bull:  { bg: 'rgba(0,212,160,0.15)', color: '#00d4a0', border: 'rgba(0,212,160,0.3)' },
  red:   { bg: 'rgba(255,71,87,0.15)', color: '#ff4757', border: 'rgba(255,71,87,0.3)' },
  bear:  { bg: 'rgba(255,71,87,0.15)', color: '#ff4757', border: 'rgba(255,71,87,0.3)' },
  blue:  { bg: 'rgba(74,158,255,0.15)', color: '#4a9eff', border: 'rgba(74,158,255,0.3)' },
  info:  { bg: 'rgba(74,158,255,0.15)', color: '#4a9eff', border: 'rgba(74,158,255,0.3)' },
  neutral: { bg: 'rgba(107,107,138,0.15)', color: '#6b6b8a', border: 'rgba(107,107,138,0.3)' },
};

export function Badge({ children, variant = 'neutral' }: BadgeProps) {
  const c = colors[variant];
  return (
    <span style={{
      background: c.bg, color: c.color, border: `1px solid ${c.border}`,
      borderRadius: '6px', padding: '2px 8px', fontSize: '11px', fontWeight: 600,
      letterSpacing: '0.5px', textTransform: 'uppercase' as const,
    }}>
      {children}
    </span>
  );
}
