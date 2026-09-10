import type {
  AgentConfig,
  AgentEvent,
  AgentStatus,
  BacktestRun,
  CalendarView,
  CycleReport,
  DecisionRow,
  Performance,
  PositionView,
  Quote,
  Trade,
} from '@/types';

const BASE = '/api';

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    cache: 'no-store',
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      /* keep the status text */
    }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; mode: string; broker_configured: boolean }>('/health'),

  // Agent
  status: () => request<AgentStatus>('/agent/status'),
  config: () => request<AgentConfig>('/agent/config'),
  start: () => request<{ enabled: boolean; message: string }>('/agent/start', { method: 'POST' }),
  stop: () => request<{ enabled: boolean; message: string }>('/agent/stop', { method: 'POST' }),
  evaluate: () => request<CycleReport>('/agent/cycle?force=true', { method: 'POST' }),
  flatten: (reason = 'closed from the console') =>
    request<{ closed: number; actions: string[] }>('/agent/flatten', {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  resetHalt: () => request<{ halted: boolean; message: string }>('/agent/reset-halt', { method: 'POST' }),
  decisions: (limit = 40) => request<DecisionRow[]>(`/agent/decisions?limit=${limit}`),
  events: (limit = 40) => request<AgentEvent[]>(`/agent/events?limit=${limit}`),

  // Market
  price: () => request<Quote>('/market/price'),
  calendar: (hours = 48) => request<CalendarView>(`/market/calendar?hours=${hours}`),

  // Trades
  trades: (limit = 100) => request<Trade[]>(`/trades?limit=${limit}`),
  openPositions: () => request<PositionView[]>('/trades/open'),
  performance: () => request<Performance>('/trades/performance'),

  // Backtest
  runBacktest: (body: { days: number; starting_balance: number; assumed_spread: number }) =>
    request<{ run_id: string; status: string }>('/backtest/run', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  backtestRun: (id: string) => request<BacktestRun>(`/backtest/runs/${id}`),
  backtestRuns: () => request<BacktestRun[]>('/backtest/runs'),
};
