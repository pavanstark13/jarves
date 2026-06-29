import { StatsGrid } from '@/components/analytics/StatsGrid';
import { PerformanceCharts } from '@/components/analytics/PerformanceCharts';
import { SessionHeatmap } from '@/components/analytics/SessionHeatmap';
import { PerformanceStats } from '@/types/trade';

const MOCK_STATS: PerformanceStats = {
  total_trades: 39,
  win_rate: 68.4,
  profit_factor: 2.14,
  expectancy: 0.82,
  max_drawdown: 3.1,
  avg_r: 1.34,
  avg_r_multiple: 1.34,
  best_session: 'London',
  worst_session: 'Asia',
  total_pnl: 647.00,
  avg_confidence: 79.2,
  equity_curve: [
    { date: '2026-06-01', equity: 10000 },
    { date: '2026-06-05', equity: 10184 },
    { date: '2026-06-08', equity: 10095 },
    { date: '2026-06-12', equity: 10312 },
    { date: '2026-06-15', equity: 10189 },
    { date: '2026-06-18', equity: 10445 },
    { date: '2026-06-22', equity: 10380 },
    { date: '2026-06-25', equity: 10520 },
    { date: '2026-06-29', equity: 10647 },
  ],
  monthly_returns: [
    { month: 'Feb', return: 2.1 },
    { month: 'Mar', return: -0.8 },
    { month: 'Apr', return: 3.4 },
    { month: 'May', return: 1.9 },
    { month: 'Jun', return: 6.47 },
  ],
  win_loss_distribution: [
    { label: 'Week 1', wins: 4, losses: 2 },
    { label: 'Week 2', wins: 6, losses: 1 },
    { label: 'Week 3', wins: 3, losses: 3 },
    { label: 'Week 4', wins: 5, losses: 2 },
    { label: 'Week 5', wins: 9, losses: 4 },
  ],
  session_performance: [
    { session: 'London', trades: 18, win_rate: 72.2, avg_r: 1.41 },
    { session: 'New York', trades: 14, win_rate: 64.3, avg_r: 1.18 },
    { session: 'Overlap', trades: 5, win_rate: 80.0, avg_r: 1.87 },
    { session: 'Asia', trades: 2, win_rate: 50.0, avg_r: 0.42 },
  ],
};

export default function AnalyticsPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Performance Analytics</h1>
        <p className="text-text-muted text-sm mt-0.5">Measure more than profit</p>
      </div>
      <StatsGrid stats={MOCK_STATS} />
      <PerformanceCharts stats={MOCK_STATS} />
      <SessionHeatmap stats={MOCK_STATS} />
    </div>
  );
}
