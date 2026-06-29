import { AnalysisResult, RiskCheckResult, RiskCheckInput } from '@/types/analysis';
import { MarketData } from '@/types/market';
import { Trade, PerformanceStats } from '@/types/trade';

const BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  getMarketData: (symbol: string, timeframe = 'H1') =>
    request<MarketData>(`/market-data/${symbol}?timeframe=${timeframe}`),

  runAnalysis: (input: { symbol: string; timeframe: string; ohlcv_data: unknown[] }) =>
    request<AnalysisResult>('/analysis/run', {
      method: 'POST',
      body: JSON.stringify(input),
    }),

  checkRisk: (input: RiskCheckInput) =>
    request<RiskCheckResult>('/risk/check', {
      method: 'POST',
      body: JSON.stringify(input),
    }),

  getTrades: () => request<Trade[]>('/journal/trades'),

  createTrade: (trade: Partial<Trade>) =>
    request<Trade>('/journal/trades', {
      method: 'POST',
      body: JSON.stringify(trade),
    }),

  getPerformance: () => request<PerformanceStats>('/analytics/performance'),

  // Backtest
  runBacktest: (params: { symbol: string; start_date: string; end_date: string; initial_balance?: number }) =>
    request<{ run_id: string; status: string }>('/backtest/run', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
  getBacktestRuns: () => request<BacktestRun[]>('/backtest/runs'),
  getBacktestRun:  (id: string) => request<BacktestRunDetail>(`/backtest/runs/${id}`),
  getBacktestTrades: (id: string, page = 1, result?: string) =>
    request<{ total: number; page: number; trades: BacktestTradeItem[] }>(
      `/backtest/runs/${id}/trades?page=${page}${result ? `&result=${result}` : ''}`
    ),

  getAnalyticsSummary: () => request<Record<string, unknown>>('/analytics/summary'),

  // Auto Trade
  getScannerStatus: () => request<ScannerStatus>('/auto-trade/status'),
  toggleScanner: (enabled: boolean) =>
    request<{ enabled: boolean; message: string }>('/auto-trade/toggle', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    }),
  triggerScan: () => request<{ signals_fired: number; signals: unknown[] }>('/auto-trade/scan', { method: 'POST' }),
  getOpenPositions: () => request<OandaPosition[]>('/auto-trade/positions'),
  getOandaAccount: () => request<OandaAccount>('/auto-trade/account'),
  closePosition: (symbol: string) =>
    request<unknown>(`/auto-trade/close/${symbol}`, { method: 'POST' }),
};

// Types for backtest and auto-trade
export interface BacktestRun {
  run_id: string; symbol: string; status: string; started_at: string;
  completed_at?: string; total_trades?: number; win_rate?: number;
  profit_factor?: number; total_pnl?: number; final_balance?: number; error?: string;
}

export interface BacktestRunDetail extends BacktestRun {
  initial_balance: number;
  wins: number; losses: number; max_drawdown_pct: number; expectancy_r: number;
  equity_curve: { timestamp: string; equity: number }[];
  per_symbol?: Record<string, BacktestRun>;
}

export interface BacktestTradeItem {
  symbol: string; direction: string; entry_time: string; exit_time: string;
  entry_price: number; exit_price: number; stop_loss: number; take_profit: number;
  result: string; r_multiple: number; pnl_usd: number; session: string; exit_reason: string;
}

export interface ScannerSignalItem {
  symbol: string; direction: string; entry_price: number; stop_loss: number;
  take_profit: number; risk_reward: number; session: string; fired_at: string;
  placement_status: string; placement_error: string; oanda_order_id: string; reasoning: string;
}

export interface ScannerStatus {
  enabled: boolean; last_scan_at: string; next_scan_at: string;
  signals_today: number; open_symbols: string[]; signals_feed: ScannerSignalItem[];
}

export interface OandaPosition {
  symbol: string; direction: string; units: number; avg_price: number; unrealized: number;
}

export interface OandaAccount {
  id: string; balance: number; nav: number; unrealized: number;
  margin_used: number; currency: string; mode: string;
}
