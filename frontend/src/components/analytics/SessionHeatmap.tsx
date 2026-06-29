import { Card } from '@/components/ui/Card';
import type { PerformanceStats } from '@/types/trade';

interface Props { stats: PerformanceStats; }

export function SessionHeatmap({ stats }: Props) {
  return (
    <Card>
      <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '16px' }}>Performance by Session</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
        <thead>
          <tr>
            {['Session', 'Trades', 'Win Rate', 'Avg R', 'Score'].map(h => (
              <th key={h} style={{ padding: '10px 16px', textAlign: 'left', color: '#6b6b8a', fontSize: '11px', fontWeight: 500, borderBottom: '1px solid #1e1e2e' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {stats.session_performance.sort((a, b) => b.win_rate - a.win_rate).map((s, i) => {
            const score = Math.round((s.win_rate / 100) * 0.6 * 100 + s.avg_r / 3 * 0.4 * 100);
            const color = score >= 70 ? '#00d4a0' : score >= 50 ? '#f5a623' : '#ff4757';
            return (
              <tr key={s.session} style={{ borderBottom: '1px solid #1e1e2e', background: i === 0 ? 'rgba(0,212,160,0.04)' : 'transparent' }}>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {i === 0 && <span style={{ fontSize: '10px', color: '#00d4a0' }}>★</span>}
                    <span style={{ fontWeight: 600, color: '#e8e8f0' }}>{s.session}</span>
                  </div>
                </td>
                <td style={{ padding: '14px 16px', color: '#e8e8f0', fontFamily: 'monospace' }}>{s.trades}</td>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '80px', height: '6px', background: '#1e1e2e', borderRadius: '3px' }}>
                      <div style={{ width: `${s.win_rate}%`, height: '100%', background: color, borderRadius: '3px' }} />
                    </div>
                    <span style={{ fontFamily: 'monospace', color, fontWeight: 600 }}>{s.win_rate.toFixed(1)}%</span>
                  </div>
                </td>
                <td style={{ padding: '14px 16px', fontFamily: 'monospace', color: s.avg_r >= 1 ? '#00d4a0' : '#ff4757', fontWeight: 600 }}>{s.avg_r >= 0 ? '+' : ''}{s.avg_r.toFixed(2)}R</td>
                <td style={{ padding: '14px 16px' }}>
                  <div style={{ display: 'inline-block', padding: '4px 12px', borderRadius: '12px', background: `${color}20`, border: `1px solid ${color}40`, color, fontSize: '12px', fontWeight: 700 }}>{score}</div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}
