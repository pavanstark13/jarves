'use client';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Card } from '@/components/ui/Card';

const equityData = [
  { date: 'Jun 1', balance: 10000 },
  { date: 'Jun 5', balance: 10184 },
  { date: 'Jun 8', balance: 10095 },
  { date: 'Jun 12', balance: 10312 },
  { date: 'Jun 15', balance: 10189 },
  { date: 'Jun 18', balance: 10445 },
  { date: 'Jun 22', balance: 10380 },
  { date: 'Jun 25', balance: 10520 },
  { date: 'Jun 29', balance: 10647 },
];

export function PerformanceCharts() {
  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-4">Equity Curve</h3>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={equityData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
          <XAxis dataKey="date" tick={{ fill: '#6b6b8a', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `$${v.toLocaleString()}`}
            domain={['dataMin - 200', 'dataMax + 200']}
          />
          <Tooltip
            contentStyle={{ background: '#12121a', border: '1px solid #1e1e2e', borderRadius: 8 }}
            labelStyle={{ color: '#6b6b8a' }}
            formatter={(v: number) => [`$${v.toLocaleString()}`, 'Balance']}
          />
          <Line
            type="monotone" dataKey="balance"
            stroke="#00d4a0" strokeWidth={2}
            dot={{ fill: '#00d4a0', r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
