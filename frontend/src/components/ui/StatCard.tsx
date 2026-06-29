import { Card } from './Card';
import { cn } from '@/lib/utils';

interface StatCardProps {
  label: string;
  value: string;
  subValue?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
}

export function StatCard({ label, value, subValue, trend, icon }: StatCardProps) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between mb-1">
        <p className="text-xs text-text-muted uppercase tracking-wider">{label}</p>
        {icon}
      </div>
      <p className={cn(
        'text-2xl font-bold font-mono',
        trend === 'up' ? 'text-bull' : trend === 'down' ? 'text-bear' : 'text-text-primary',
      )}>
        {value}
      </p>
      {subValue && <p className="text-xs text-text-muted mt-1">{subValue}</p>}
    </Card>
  );
}
