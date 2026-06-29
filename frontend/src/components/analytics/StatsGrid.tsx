import { Card } from '@/components/ui/Card';
import type { PerformanceStats } from '@/types/trade';

interface Props { stats: PerformanceStats; }

export function StatsGrid({ stats }: Props) {
  const items = [
    { label: 'Win Rate', value: `${stats.win_rate.toFixed(1)}%`, color: '#00d4a0', desc: `${stats.total_trades} total trades` },
    { label: 'Profit Factor', value: stats.profit_factor.toFixed(2), color: '#4a9eff', desc: 'Gross profit / loss' },
    { label: 'Expectancy', value: `${stats.expectancy.toFixed(2)}R`, color: '#4a9eff', desc: 'Per trade avg' },
    { label: 'Max Drawdown', value: `${stats.max_drawdown.toFixed(1)}%`, color: '#ff4757', desc: 'Peak to trough' },
    { label: 'Avg R Multiple', value: `${stats.avg_r.toFixed(2)}R`, color: '#00d4a0', desc: 'Average winner' },
    { label: 'Total P&L', value: `$${stats.total_pnl.toFixed(0)}`, color: '#00d4a0', desc: 'All time' },
    { label: 'Best Session', value: stats.best_session, color: '#4a9eff', desc: 'By win rate' },
    { label: 'Total Trades', value: String(stats.total_trades), color: '#e8e8f0', desc: 'Recorded' },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
      {items.map(item => (
        <Card key={item.label}>
          <div style={{ fontSize: '11px', color: '#6b6b8a', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>{item.label}</div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: item.color, fontFamily: 'monospace', marginBottom: '4px' }}>{item.value}</div>
          <div style={{ fontSize: '11px', color: '#6b6b8a' }}>{item.desc}</div>
        </Card>
      ))}
    </div>
  );
}
