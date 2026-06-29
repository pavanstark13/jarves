'use client';
import { useEffect, useState } from 'react';
import { StatsGrid } from '@/components/analytics/StatsGrid';
import { PerformanceCharts } from '@/components/analytics/PerformanceCharts';
import { SessionHeatmap } from '@/components/analytics/SessionHeatmap';
import { PerformanceStats } from '@/types/trade';
import { api } from '@/lib/api';

function toPerformanceStats(d: Record<string, unknown>): PerformanceStats {
  const sessions = (d.session_stats ?? {}) as Record<string, { total: number; win_rate: number }>;
  const SESSION_LABELS: Record<string, string> = { LONDON: 'London', NEW_YORK: 'New York', OVERLAP: 'Overlap', ASIA: 'Asia', KILL_ZONE: 'Kill Zone' };
  const session_performance = Object.entries(sessions).map(([k, v]) => ({
    session: SESSION_LABELS[k] ?? k,
    trades: v.total,
    win_rate: Math.round(v.win_rate * 100 * 10) / 10,
    avg_r: 0,
  }));
  const bestSess = session_performance.sort((a, b) => b.win_rate - a.win_rate)[0]?.session ?? '';
  const worstSess = session_performance[session_performance.length - 1]?.session ?? '';

  return {
    total_trades: Number(d.total_trades ?? 0),
    win_rate: Math.round(Number(d.win_rate ?? 0) * 1000) / 10,
    profit_factor: Number(d.profit_factor ?? 0),
    expectancy: Number(d.expectancy_r ?? 0),
    max_drawdown: Number(d.max_drawdown_pct ?? 0),
    avg_r: Number(d.expectancy_r ?? 0),
    avg_r_multiple: Number(d.expectancy_r ?? 0),
    best_session: bestSess,
    worst_session: worstSess,
    total_pnl: Number(d.total_pnl ?? 0),
    avg_confidence: 0,
    equity_curve: [],
    monthly_returns: [],
    win_loss_distribution: [],
    session_performance,
  };
}

const EMPTY: PerformanceStats = {
  total_trades: 0, win_rate: 0, profit_factor: 0, expectancy: 0,
  max_drawdown: 0, avg_r: 0, avg_r_multiple: 0, best_session: '', worst_session: '',
  total_pnl: 0, avg_confidence: 0, equity_curve: [], monthly_returns: [],
  win_loss_distribution: [], session_performance: [],
};

export default function AnalyticsPage() {
  const [stats, setStats] = useState<PerformanceStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAnalyticsSummary()
      .then((d) => setStats(toPerformanceStats(d as Record<string, unknown>)))
      .catch(() => setStats(EMPTY))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Performance Analytics</h1>
        <p className="text-text-muted text-sm mt-0.5">Real data from your trade journal</p>
      </div>
      {loading ? (
        <div style={{ color: '#5a5a7a', padding: '40px', textAlign: 'center' }}>Loading trade data…</div>
      ) : (stats?.total_trades ?? 0) === 0 ? (
        <div style={{ background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '60px', textAlign: 'center', color: '#5a5a7a' }}>
          <div style={{ fontSize: '16px', marginBottom: '8px' }}>No closed trades yet</div>
          <div style={{ fontSize: '12px' }}>Analytics will appear once trades are recorded in your journal.</div>
        </div>
      ) : (
        <>
          <StatsGrid stats={stats!} />
          <PerformanceCharts stats={stats!} />
          <SessionHeatmap stats={stats!} />
        </>
      )}
    </div>
  );
}
