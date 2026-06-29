export type TradeDirection = 'LONG' | 'SHORT';
export type TradeStatus = 'OPEN' | 'CLOSED' | 'CANCELLED';

export interface Trade {
  id: string;
  symbol: string;
  direction: TradeDirection;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  position_size: number;
  status: TradeStatus;
  entry_time: string;
  exit_time?: string;
  exit_price?: number;
  pnl?: number;
  r_multiple?: number;
  setup_quality: number;
  confidence_score: number;
  trade_direction: string;
  session: string;
  notes?: string;
  ai_explanation?: string;
  result?: string;
  created_at?: string;
}

export interface SessionPerf {
  session: string;
  trades: number;
  win_rate: number;
  avg_r: number;
}

export type TradeFormData = Partial<Trade>;

export interface PerformanceStats {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  max_drawdown: number;
  avg_r: number;
  avg_r_multiple: number;
  best_session: string;
  worst_session: string;
  total_pnl: number;
  avg_confidence: number;
  equity_curve: { date: string; equity: number }[];
  monthly_returns: { month: string; return: number }[];
  win_loss_distribution: { label: string; wins: number; losses: number }[];
  session_performance: SessionPerf[];
}
