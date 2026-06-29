import { Card } from '@/components/ui/Card';

const sessions = [
  { name: 'London', trades: 18, win_rate: 72, avg_r: 1.41, pnl: 342.50 },
  { name: 'New York', trades: 14, win_rate: 64, avg_r: 1.18, pnl: 189.00 },
  { name: 'Overlap', trades: 5, win_rate: 80, avg_r: 1.87, pnl: 221.00 },
  { name: 'Asia', trades: 2, win_rate: 50, avg_r: 0.42, pnl: -38.50 },
];

export function SessionHeatmap() {
  return (
    <Card className="p-5">
      <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-4">Performance by Session</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-text-muted text-xs border-b border-border">
            {['Session', 'Trades', 'Win Rate', 'Avg R', 'P&L'].map((h) => (
              <th key={h} className="pb-2 text-left font-medium pr-6">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.name} className="border-b border-border/30">
              <td className="py-3 pr-6 font-medium">{s.name}</td>
              <td className="pr-6 text-text-muted">{s.trades}</td>
              <td className={`pr-6 font-medium ${s.win_rate >= 65 ? 'text-bull' : s.win_rate >= 50 ? 'text-info' : 'text-bear'}`}>
                {s.win_rate}%
              </td>
              <td className={`pr-6 font-mono ${s.avg_r >= 1 ? 'text-bull' : 'text-bear'}`}>
                {s.avg_r >= 0 ? '+' : ''}{s.avg_r}R
              </td>
              <td className={`font-mono font-medium ${s.pnl >= 0 ? 'text-bull' : 'text-bear'}`}>
                {s.pnl >= 0 ? '+' : ''}${Math.abs(s.pnl).toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
