'use client';
import { Card } from '@/components/ui/Card';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { PerformanceStats } from '@/types/trade';

interface Props { stats: PerformanceStats; }

const chartTheme = {
  background: 'transparent',
  grid: '#1e1e2e',
  text: '#6b6b8a',
};

export function PerformanceCharts({ stats }: Props) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '16px' }}>
      <Card>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '20px' }}>Equity Curve</h3>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={stats.equity_curve}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis dataKey="date" tick={{ fill: chartTheme.text, fontSize: 11 }} tickFormatter={v => v.slice(5)} />
            <YAxis tick={{ fill: chartTheme.text, fontSize: 11 }} tickFormatter={v => `$${v.toLocaleString()}`} />
            <Tooltip
              contentStyle={{ background: '#12121a', border: '1px solid #1e1e2e', borderRadius: '8px', color: '#e8e8f0' }}
              formatter={(v: number) => [`$${v.toLocaleString()}`, 'Equity']}
            />
            <Line type="monotone" dataKey="equity" stroke="#4a9eff" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <Card>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '20px' }}>Monthly Returns</h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={stats.monthly_returns}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis dataKey="month" tick={{ fill: chartTheme.text, fontSize: 11 }} />
            <YAxis tick={{ fill: chartTheme.text, fontSize: 11 }} tickFormatter={v => `${v}%`} />
            <Tooltip
              contentStyle={{ background: '#12121a', border: '1px solid #1e1e2e', borderRadius: '8px', color: '#e8e8f0' }}
              formatter={(v: number) => [`${v}%`, 'Return']}
            />
            <Bar dataKey="return" fill="#4a9eff" radius={[4, 4, 0, 0]}
              label={false}
              style={{ fill: '#4a9eff' }}
            />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card style={{ gridColumn: 'span 2' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '20px' }}>Win/Loss Distribution</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={stats.win_loss_distribution}>
            <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
            <XAxis dataKey="label" tick={{ fill: chartTheme.text, fontSize: 11 }} />
            <YAxis tick={{ fill: chartTheme.text, fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#12121a', border: '1px solid #1e1e2e', borderRadius: '8px', color: '#e8e8f0' }} />
            <Bar dataKey="wins" fill="#00d4a0" radius={[4, 4, 0, 0]} name="Wins" />
            <Bar dataKey="losses" fill="#ff4757" radius={[4, 4, 0, 0]} name="Losses" />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}
