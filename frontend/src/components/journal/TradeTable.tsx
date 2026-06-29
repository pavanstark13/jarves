'use client';
import { Trade } from '@/types/trade';
import { Badge } from '@/components/ui/Badge';
import { formatR } from '@/lib/utils';

const MOCK_TRADES: Trade[] = [
  { id: '1', symbol: 'XAUUSD', direction: 'LONG', entry_price: 2341.20, stop_loss: 2329.00, take_profit: 2365.00, position_size: 0.05, status: 'CLOSED', entry_time: '2026-06-27T09:15:00Z', exit_time: '2026-06-27T14:30:00Z', exit_price: 2363.50, pnl: 111.50, r_multiple: 1.85, setup_quality: 82, confidence_score: 0.82, trade_direction: 'LONG', session: 'London' },
  { id: '2', symbol: 'EURUSD', direction: 'SHORT', entry_price: 1.09120, stop_loss: 1.09380, take_profit: 1.08340, position_size: 0.10, status: 'CLOSED', entry_time: '2026-06-26T14:00:00Z', exit_time: '2026-06-26T16:45:00Z', exit_price: 1.08920, pnl: 200.00, r_multiple: 0.77, setup_quality: 71, confidence_score: 0.71, trade_direction: 'SHORT', session: 'NY' },
  { id: '3', symbol: 'GBPUSD', direction: 'LONG', entry_price: 1.26840, stop_loss: 1.26480, take_profit: 1.27920, position_size: 0.08, status: 'CLOSED', entry_time: '2026-06-25T08:30:00Z', exit_time: '2026-06-25T13:00:00Z', exit_price: 1.26600, pnl: -192.00, r_multiple: -0.67, setup_quality: 68, confidence_score: 0.68, trade_direction: 'LONG', session: 'London' },
  { id: '4', symbol: 'XAUUSD', direction: 'LONG', entry_price: 2374.50, stop_loss: 2362.00, take_profit: 2409.50, position_size: 0.05, status: 'OPEN', entry_time: '2026-06-29T10:30:00Z', pnl: 64.75, setup_quality: 87, confidence_score: 0.87, trade_direction: 'LONG', session: 'NY' },
];

export function TradeTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-text-muted text-xs border-b border-border">
            {['Date', 'Symbol', 'Dir', 'Entry', 'Exit', 'SL', 'TP', 'Size', 'Quality', 'R', 'P&L', 'Status'].map((h) => (
              <th key={h} className="pb-3 text-left font-medium pr-4">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {MOCK_TRADES.map((t) => (
            <tr key={t.id} className="border-b border-border/30 hover:bg-border/10 transition-colors">
              <td className="py-3 pr-4 text-text-muted text-xs whitespace-nowrap">
                {new Date(t.entry_time).toLocaleDateString()}
              </td>
              <td className="pr-4 font-medium">{t.symbol}</td>
              <td className="pr-4">
                <Badge variant={t.direction === 'LONG' ? 'bull' : 'bear'}>{t.direction}</Badge>
              </td>
              <td className="pr-4 font-mono">{t.entry_price}</td>
              <td className="pr-4 font-mono text-text-muted">{t.exit_price ?? '—'}</td>
              <td className="pr-4 font-mono text-bear">{t.stop_loss}</td>
              <td className="pr-4 font-mono text-bull">{t.take_profit}</td>
              <td className="pr-4 font-mono">{t.position_size}</td>
              <td className="pr-4">
                <span className={`text-xs font-medium ${t.setup_quality >= 80 ? 'text-bull' : t.setup_quality >= 65 ? 'text-info' : 'text-bear'}`}>
                  {t.setup_quality}
                </span>
              </td>
              <td className={`pr-4 font-mono font-medium ${(t.r_multiple ?? 0) >= 0 ? 'text-bull' : 'text-bear'}`}>
                {t.r_multiple != null ? formatR(t.r_multiple) : '—'}
              </td>
              <td className={`pr-4 font-mono font-medium ${(t.pnl ?? 0) >= 0 ? 'text-bull' : 'text-bear'}`}>
                {t.pnl != null ? `${t.pnl >= 0 ? '+' : ''}$${Math.abs(t.pnl).toFixed(2)}` : '—'}
              </td>
              <td>
                <Badge variant={t.status === 'OPEN' ? 'info' : t.status === 'CLOSED' ? 'neutral' : 'bear'}>
                  {t.status}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
