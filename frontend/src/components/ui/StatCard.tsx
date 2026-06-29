import { Card } from './Card';

interface StatCardProps {
  title: string;
  value: string;
  change: string;
  changePct: string;
  positive: boolean;
  icon?: React.ReactNode;
}

export function StatCard({ title, value, change, changePct, positive, icon }: StatCardProps) {
  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <span style={{ color: '#6b6b8a', fontSize: '12px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{title}</span>
        {icon}
      </div>
      <div style={{ fontSize: '28px', fontWeight: 700, color: '#e8e8f0', marginBottom: '8px', fontFamily: 'monospace' }}>{value}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '12px', color: '#6b6b8a' }}>{change}</span>
        {changePct && (
          <span style={{ fontSize: '12px', fontWeight: 600, color: positive ? '#00d4a0' : '#ff4757' }}>{changePct}</span>
        )}
      </div>
    </Card>
  );
}
