export interface OHLCV {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MarketData {
  symbol: string;
  timeframe: string;
  current_price: number;
  change_24h: number;
  change_pct_24h: number;
  high_24h: number;
  low_24h: number;
  ohlcv: OHLCV[];
}

export type Symbol = 'XAUUSD' | 'EURUSD' | 'GBPUSD' | 'US30';
export type Timeframe = 'M5' | 'M15' | 'H1' | 'H4' | 'D1';
