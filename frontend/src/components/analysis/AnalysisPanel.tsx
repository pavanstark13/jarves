'use client';
import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { EngineResult } from './EngineResult';
import { ConfidenceScore } from './ConfidenceScore';
import { Loader2, AlertCircle } from 'lucide-react';
import type { AnalysisResult, RiskCheckResult } from '@/types/analysis';

const SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'US30'];
const TIMEFRAMES = ['M5', 'M15', 'H1', 'H4', 'D1'];

export function AnalysisPanel() {
  const [symbol, setSymbol] = useState('XAUUSD');
  const [timeframe, setTimeframe] = useState('H1');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [riskResult, setRiskResult] = useState<RiskCheckResult | null>(null);

  async function runAnalysis() {
    setLoading(true);
    setError(null);
    setResult(null);
    setRiskResult(null);

    try {
      // Step 1: fetch real OHLCV data
      const mktRes = await fetch(`/api/market-data/${symbol}?timeframe=${timeframe}&count=300`);
      if (!mktRes.ok) throw new Error(`Market data: ${await mktRes.text()}`);
      const mktData = await mktRes.json();

      // Step 2: run analysis on real bars
      const analysisRes = await fetch('/api/analysis/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, timeframe, ohlcv_data: mktData.bars }),
      });
      if (!analysisRes.ok) throw new Error(`Analysis: ${await analysisRes.text()}`);
      const analysis: AnalysisResult = await analysisRes.json();
      setResult(analysis);

      // Step 3: run risk check
      if (analysis.trade_direction !== 'NO_TRADE' && analysis.engines?.length) {
        const lastBar = mktData.bars[mktData.bars.length - 1];
        const riskRes = await fetch('/api/risk/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symbol,
            direction: analysis.trade_direction,
            setup_quality: analysis.setup_quality,
            entry_price: lastBar?.close ?? 0,
            stop_loss: 0,
            take_profit: 0,
            account_balance: 10000,
          }),
        });
        if (riskRes.ok) setRiskResult(await riskRes.json());
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }

  const selectCls = "bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-info";

  return (
    <div className="space-y-6">
      {/* Controls */}
      <Card className="p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="text-xs text-text-muted uppercase tracking-wider block mb-1.5">Symbol</label>
            <select value={symbol} onChange={e => setSymbol(e.target.value)} className={selectCls}>
              {SYMBOLS.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-text-muted uppercase tracking-wider block mb-1.5">Timeframe</label>
            <select value={timeframe} onChange={e => setTimeframe(e.target.value)} className={selectCls}>
              {TIMEFRAMES.map(t => <option key={t}>{t}</option>)}
            </select>
          </div>
          <Button onClick={runAnalysis} disabled={loading} className="flex items-center gap-2">
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {loading ? 'Fetching real data…' : 'Run Analysis'}
          </Button>
        </div>
        <p className="text-xs text-text-muted mt-3">
          Fetches live OHLCV bars from Twelve Data, then runs all 7 engines on real price action.
        </p>
      </Card>

      {/* Error */}
      {error && (
        <Card className="p-4 border-bear/30 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-bear flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-bear text-sm font-medium">Analysis failed</p>
            <p className="text-text-muted text-xs mt-1">{error}</p>
            <p className="text-text-muted text-xs mt-1">
              Make sure TWELVE_DATA_API_KEY is set in your backend .env
            </p>
          </div>
        </Card>
      )}

      {result && (
        <>
          {/* Score + AI explanation */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <ConfidenceScore score={result.setup_quality} direction={result.trade_direction} />
            <Card className="lg:col-span-2 p-5 flex flex-col">
              <p className="text-xs text-text-muted uppercase tracking-wider mb-2">AI Explanation</p>
              <p className="text-sm text-text-primary leading-relaxed flex-1">
                {result.ai_explanation || 'No AI explanation available. Set ANTHROPIC_API_KEY to enable.'}
              </p>
              <p className="text-xs text-text-muted mt-3">{new Date(result.timestamp).toLocaleString()}</p>
            </Card>
          </div>

          {/* Risk result */}
          {riskResult && (
            <Card className={`p-5 border ${riskResult.approved ? 'border-bull/30' : 'border-bear/30'}`}>
              <div className="flex items-center gap-2 mb-3">
                <div className={`w-3 h-3 rounded-full ${riskResult.approved ? 'bg-bull' : 'bg-bear'}`} />
                <span className={`font-semibold ${riskResult.approved ? 'text-bull' : 'text-bear'}`}>
                  {riskResult.approved ? 'RISK ENGINE: APPROVED' : `RISK ENGINE: REJECTED — ${riskResult.rejection_reason}`}
                </span>
              </div>
              {riskResult.approved && (
                <div className="flex gap-6 text-sm">
                  <div><span className="text-text-muted">Position size</span> <span className="font-mono text-text-primary ml-2">{riskResult.position_size} lots</span></div>
                  <div><span className="text-text-muted">Risk amount</span> <span className="font-mono text-bear ml-2">${riskResult.risk_amount?.toFixed(2)}</span></div>
                </div>
              )}
              <div className="mt-3 space-y-1">
                {riskResult.checks?.map(c => (
                  <div key={c.rule} className="flex items-center gap-2 text-xs">
                    <span className={c.passed ? 'text-bull' : 'text-bear'}>{c.passed ? '✓' : '✗'}</span>
                    <span className="text-text-muted">{c.rule}</span>
                    <span className="text-text-primary font-mono ml-auto">{c.value}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Engine results */}
          <div>
            <h3 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">Engine Breakdown</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {result.engines?.map(e => <EngineResult key={e.engine_name} engine={e} />)}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
