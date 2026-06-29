export interface EngineResult {
  engine_name: string;
  signal: 'BULLISH' | 'BEARISH' | 'NEUTRAL' | 'DETECTED' | 'CLEAR' | 'ACTIVE' | 'INACTIVE';
  confidence: number;
  details: Record<string, unknown>;
  weight: number;
}

export interface AnalysisResult {
  symbol: string;
  timeframe: string;
  timestamp: string;
  engines: EngineResult[];
  setup_quality: number;
  trade_direction: 'LONG' | 'SHORT' | 'NO_TRADE';
  ai_explanation: string;
}

export interface RiskCheckResult {
  approved: boolean;
  rejection_reason?: string;
  position_size?: number;
  risk_amount?: number;
  checks: { rule: string; passed: boolean; value: string }[];
}

export interface RiskCheckInput {
  symbol: string;
  direction: 'LONG' | 'SHORT';
  setup_quality: number;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  account_balance: number;
}
