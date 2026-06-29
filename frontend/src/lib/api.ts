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

  runAnalysis: (symbol: string, timeframe: string, ohlcv_data: unknown[]) =>
    request<AnalysisResult>('/analysis/run', {
      method: 'POST',
      body: JSON.stringify({ symbol, timeframe, ohlcv_data }),
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
};
