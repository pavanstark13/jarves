import { StatCard } from '@/components/ui/StatCard';
import { MarketOverview } from '@/components/dashboard/MarketOverview';
import { EngineStatusGrid } from '@/components/dashboard/EngineStatusGrid';
import { RiskMeter } from '@/components/dashboard/RiskMeter';
import { ActiveTrades } from '@/components/dashboard/ActiveTrades';

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Dashboard</h1>
        <p className="text-text-muted text-sm mt-0.5">Decision support — not prediction</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        <StatCard label="Account Balance" value="$10,000.00" subValue="Base capital" />
        <StatCard label="Daily P&L" value="+$64.75" subValue="+0.65%" trend="up" />
        <StatCard label="Open Trades" value="1" subValue="1 XAUUSD LONG" trend="neutral" />
        <StatCard label="Win Rate (30d)" value="68.4%" subValue="39 trades" trend="up" />
      </div>

      {/* Market overview */}
      <MarketOverview />

      {/* Engines + Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <EngineStatusGrid />
        </div>
        <RiskMeter />
      </div>

      {/* Active trades */}
      <ActiveTrades />
    </div>
  );
}
