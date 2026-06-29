'use client';
import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EngineResultCard } from './EngineResult';
import { ConfidenceScore } from './ConfidenceScore';
import { AnalysisResult } from '@/types/analysis';
import { Loader2 } from 'lucide-react';

const SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'US30'];
const TIMEFRAMES = ['M5', 'M15', 'H1', 'H4', 'D1'];

// Mock result for UI demo
const MOCK_RESULT: AnalysisResult = {
  symbol: 'XAUUSD',
  timeframe: 'H1',
  timestamp: new Date().toISOString(),
  setup_quality: 87,
  trade_direction: 'LONG',
  ai_explanation: 'Price swept sell-side liquidity below the 2370 equal lows during the London session, triggering a bullish change of character. A valid bullish order block at 2372–2374 coincides with a fair value gap. The trend is strongly bullish on H1 and H4 with EMA stacks aligned. No high-impact news for 4+ hours. Risk/reward exceeds 3.0R targeting the next supply zone at 2408.',
  engines: [
    { engine_name: 'Trend', signal: 'BULLISH', confidence: 0.92, details: { ema20_50: 'above', ema50_200: 'above', price: 'above all EMAs' }, weight: 1.5 },
    { engine_name: 'Market Structure', signal: 'BULLISH', confidence: 0.85, details: { pattern: 'Higher High confirmed', event: 'Break of Structure UP', last_swing: '2382.50' }, weight: 1.5 },
    { engine_name: 'Liquidity', signal: 'DETECTED', confidence: 0.88, details: { type: 'Sell-side sweep', level: '2369.80', candles_since: '2' }, weight: 1.2 },
    { engine_name: 'Smart Money', signal: 'DETECTED', confidence: 0.79, details: { order_block: 'Bullish OB 2372–2374', fvg: '2374.20–2376.10', mitigation: 'OB untested' }, weight: 1.3 },
    { engine_name: 'Session', signal: 'ACTIVE', confidence: 0.90, details: { current: 'NY Kill Zone', time_in_session: '45m' }, weight: 0.8 },
    { engine_name: 'News', signal: 'CLEAR', confidence: 1.0, details: { status: 'No events < 30min', next: 'NFP in 4h20m' }, weight: 1.0 },
    { engine_name: 'Volatility', signal: 'NEUTRAL', confidence: 0.70, details: { atr_14: '8.40', spread_atr_ratio: '0.06', regime: 'Normal' }, weight: 0.9 },
  ],
};

export function AnalysisPanel() {
  const [symbol, setSymbol] = useState('XAUUSD');
  const [timeframe, setTimeframe] = useState('H1');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  async function runAnalysis() {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1200)); // simulate API call
    setResult(MOCK_RESULT);
    setLoading(false);
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <Card className="p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="text-xs text-text-muted uppercase tracking-wider block mb-1.5">Symbol</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-info"
            >
              {SYMBOLS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-text-muted uppercase tracking-wider block mb-1.5">Timeframe</label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-info"
            >
              {TIMEFRAMES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </div>
          <Button onClick={runAnalysis} disabled={loading} className="flex items-center gap-2">
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {loading ? 'Analysing…' : 'Run Analysis'}
          </Button>
        </div>
      </Card>

      {result && (
        <>
          {/* Score + AI explanation */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <ConfidenceScore score={result.setup_quality} direction={`${result.trade_direction} ${result.symbol}`} />
            <Card className="lg:col-span-2 p-5 flex flex-col">
              <p className="text-xs text-text-muted uppercase tracking-wider mb-2">AI Explanation</p>
              <p className="text-sm text-text-primary leading-relaxed flex-1">{result.ai_explanation}</p>
              <p className="text-xs text-text-muted mt-3">{new Date(result.timestamp).toLocaleString()}</p>
            </Card>
          </div>

          {/* Engine results */}
          <div>
            <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">Engine Breakdown</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {result.engines.map((e) => <EngineResultCard key={e.engine_name} engine={e} />)}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
