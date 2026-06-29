import { StatCard } from '@/components/ui/StatCard';

export function StatsGrid() {
  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
      <StatCard label="Win Rate" value="68.4%" subValue="26W / 12L / 1B" trend="up" />
      <StatCard label="Profit Factor" value="2.14" subValue="Gross profit / Gross loss" trend="up" />
      <StatCard label="Expectancy" value="+0.82R" subValue="per trade average" trend="up" />
      <StatCard label="Max Drawdown" value="-3.1%" subValue="of account balance" trend="neutral" />
      <StatCard label="Avg R Multiple" value="+1.34R" subValue="closed trades" trend="up" />
      <StatCard label="Best Session" value="London" subValue="74% win rate" trend="up" />
      <StatCard label="Worst Session" value="Asia" subValue="42% win rate" trend="down" />
      <StatCard label="Avg Confidence" value="79.2%" subValue="all taken trades" trend="neutral" />
    </div>
  );
}
