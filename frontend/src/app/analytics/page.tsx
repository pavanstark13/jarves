import { StatsGrid } from '@/components/analytics/StatsGrid';
import { PerformanceCharts } from '@/components/analytics/PerformanceCharts';
import { SessionHeatmap } from '@/components/analytics/SessionHeatmap';

export default function AnalyticsPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Performance Analytics</h1>
        <p className="text-text-muted text-sm mt-0.5">Measure more than profit</p>
      </div>
      <StatsGrid />
      <PerformanceCharts />
      <SessionHeatmap />
    </div>
  );
}
