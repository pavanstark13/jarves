/** Shapes returned by the agent API. */

export interface Gate {
  name: string;
  passed: boolean;
  detail: string;
}

export interface Decision {
  time: string;
  action: 'LONG' | 'SHORT' | 'STAND_ASIDE';
  symbol: string;
  entry: number;
  stop_loss: number;
  take_profit: number;
  risk_per_unit: number;
  risk_reward: number;
  gates: Gate[];
  readings: Record<string, unknown>;
  summary: string;
}

export interface RiskCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface RiskVerdict {
  approved: boolean;
  units: number;
  risk_amount: number;
  risk_pct: number;
  notional: number;
  reason: string;
  checks: RiskCheck[];
}

export interface Quote {
  time: string;
  bid: number;
  ask: number;
  mid: number;
  spread: number;
  tradeable: boolean;
}

export interface Account {
  balance: number;
  nav: number;
  unrealized_pl: number;
  margin_available: number;
  currency: string;
  venue: string;
}

export interface PositionView {
  trade_id: string;
  direction: 'LONG' | 'SHORT';
  units: number;
  entry_price: number;
  stop_loss: number | null;
  take_profit: number | null;
  opened_at: string;
  unrealized_pl: number;
  initial_risk: number;
}

export interface DayBook {
  date: string;
  start_nav: number;
  peak_nav: number;
  realized_pl: number;
  trades_opened: number;
  consecutive_losses: number;
  cooldown_until: string | null;
  halted: boolean;
  halt_reason: string;
  daily_loss_pct?: number;
  drawdown_pct?: number;
}

export interface SessionState {
  utc_time: string;
  session: string;
  window: string;
  can_open: boolean;
  is_rollover: boolean;
  is_weekend: boolean;
  reason: string;
}

export interface CycleReport {
  time: string;
  ran: boolean;
  decision: Decision | null;
  risk: RiskVerdict | null;
  actions: string[];
  error: string;
}

export interface AgentStatus {
  symbol: string;
  enabled: boolean;
  mode: 'paper' | 'live';
  venue: string;
  broker_configured: boolean;
  started_at: string | null;
  cycles: number;
  scan_interval_seconds: number;
  halted: boolean;
  halt_reason: string;
  account: Account | null;
  quote: Quote | null;
  day: DayBook | null;
  positions: PositionView[];
  last_cycle: CycleReport | null;
  session: SessionState;
}

export interface Trade {
  id: number;
  broker_trade_id: string;
  mode: string;
  venue: string;
  status: 'OPEN' | 'CLOSED';
  direction: 'LONG' | 'SHORT';
  units: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  initial_risk: number;
  risk_amount: number;
  opened_at: string;
  closed_at: string | null;
  exit_price: number | null;
  exit_reason: string;
  realized_pl: number | null;
  r_multiple: number | null;
  session: string;
  entry_reason: string;
}

export interface DecisionRow {
  id: number;
  time: string;
  action: string;
  executed: boolean;
  entry: number;
  stop_loss: number;
  take_profit: number;
  blocker: string;
  summary: string;
  detail: Decision & { risk?: RiskVerdict };
}

export interface AgentEvent {
  id: number;
  time: string;
  kind: string;
  message: string;
}

export interface Performance {
  trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  average_win: number;
  average_loss: number;
  profit_factor: number;
  expectancy_r: number;
  best_trade: number;
  worst_trade: number;
  max_consecutive_losses: number;
  by_session: Record<string, { trades: number; pnl: number; win_rate: number }>;
  by_exit_reason: Record<string, number>;
  equity_curve: { time: string; cumulative_pnl: number; pnl: number; r_multiple: number }[];
}

export interface CalendarEvent {
  name: string;
  scheduled_at: string;
  impact: string;
  currency: string;
  source: string;
}

export interface CalendarView {
  source: string;
  blackout: { active: boolean; minutes_away: number; reason: string; event: CalendarEvent | null };
  events: CalendarEvent[];
}

export interface AgentConfig {
  mode: string;
  broker_environment: string;
  scan_interval_seconds: number;
  risk: Record<string, number>;
  trade: Record<string, number>;
  market: Record<string, string | number>;
}

export interface BacktestSummary {
  symbol: string;
  start: string;
  end: string;
  bars_tested: number;
  starting_balance: number;
  ending_balance: number;
  total_pnl: number;
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  profit_factor: number;
  expectancy_r: number;
  max_drawdown_pct: number;
  assumed_spread: number;
  note: string;
  equity_curve: { time: string; equity: number }[];
  trades?: BacktestTrade[];
}

export interface BacktestTrade {
  direction: string;
  units: number;
  entry_time: string;
  entry_price: number;
  exit_time: string;
  exit_price: number;
  stop_loss: number;
  take_profit: number;
  r_multiple: number;
  pnl: number;
  exit_reason: string;
  session: string;
}

export interface BacktestRun {
  run_id: string;
  status: 'RUNNING' | 'COMPLETE' | 'FAILED';
  started_at: string;
  finished_at?: string;
  request: { days: number; starting_balance: number; assumed_spread: number };
  result?: BacktestSummary;
  error?: string;
}
