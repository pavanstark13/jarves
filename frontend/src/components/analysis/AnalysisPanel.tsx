'use client';
import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { EngineResult } from './EngineResult';
import { ConfidenceScore } from './ConfidenceScore';
import { Play, CheckCircle, XCircle } from 'lucide-react';
import { api } from '@/lib/api';
import type { AnalysisResult, RiskCheckResult } from '@/types/analysis';

const SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'US30'];
const TIMEFRAMES = ['M5', 'M15', 'H1', 'H4', 'D1'];

const MOCK_RESULT: AnalysisResult = {
  symbol: 'XAUUSD', timeframe: 'H1', timestamp: new Date().toISOString(),
  setup_quality: 78, trade_direction: 'LONG',
  ai_explanation: 'Strong bullish market structure on H1 with clear MSS above previous high. Active demand order block at 2310-2315 providing confluence. FVG present between 2312-2315 acting as magnet. Liquidity pool above 2330 is likely target. London session provides ideal entry window. Setup scores 78/100 — recommended to proceed with standard 1% risk.',
  engines: [
    { engine_name: 'Market Structure', signal: 'BULLISH', confidence: 0.82, details: { trend: 'uptrend', last_mss: 'H1 @ 2315' }, weight: 0.20 },
    { engine_name: 'Order Blocks', signal: 'DETECTED', confidence: 0.76, details: { ob_type: 'demand', price: '2310-2315' }, weight: 0.18 },
    { engine_name: 'Fair Value Gaps', signal: 'ACTIVE', confidence: 0.68, details: { fvg_range: '2312-2315', filled: '30%' }, weight: 0.15 },
    { engine_name: 'Liquidity Map', signal: 'BULLISH', confidence: 0.71, details: { pool_above: '2330', pool_below: '2305' }, weight: 0.17 },
    { engine_name: 'Session Profile', signal: 'NEUTRAL', confidence: 0.50, details: { session: 'OVERLAP', bias: 'neutral' }, weight: 0.10 },
    { engine_name: 'Fibonacci', signal: 'BULLISH', confidence: 0.78, details: { level: '0.618', price: '2311.20' }, weight: 0.10 },
    { engine_name: 'RSI Momentum', signal: 'NEUTRAL', confidence: 0.55, details: { rsi: '52.4', divergence: 'none' }, weight: 0.10 },
  ],
};

const MOCK_RISK: RiskCheckResult = {
  approved: true, position_size: 0.12, risk_amount: 100.00,
  checks: [
    { rule: 'Daily loss limit', passed: true, value: '1.2% / 3% used' },
    { rule: 'Max open trades', passed: true, value: '2 / 5 open' },
    { rule: 'Min setup quality', passed: true, value: '78 >= 65' },
    { rule: 'Risk/Reward ratio', passed: true, value: '1:2.7 >= 1:2' },
    { rule: 'Session filter', passed: true, value: 'London session' },
  ],
};

export function AnalysisPanel() {
  const [symbol, setSymbol] = useState('XAUUSD');
  const [timeframe, setTimeframe] = useState('H1');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [riskResult, setRiskResult] = useState<RiskCheckResult | null>(null);

  async function handleRun() {
    setLoading(true);
    try {
      const data = await api.runAnalysis({ symbol, timeframe, ohlcv_data: [] });
      setResult(data);
    } catch {
      setResult(MOCK_RESULT);
    }
    try {
      const risk = await api.checkRisk({
        symbol, direction: 'LONG', setup_quality: 78,
        entry_price: 2318.50, stop_loss: 2310.00, take_profit: 2345.00, account_balance: 10000,
      });
      setRiskResult(risk);
    } catch {
      setRiskResult(MOCK_RISK);
    }
    setLoading(false);
  }

  const selectStyle = {
    background: '#0a0a0f', border: '1px solid #1e1e2e', color: '#e8e8f0',
    borderRadius: '8px', padding: '8px 12px', fontSize: '14px', cursor: 'pointer',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Controls */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div>
            <label style={{ fontSize: '12px', color: '#6b6b8a', display: 'block', marginBottom: '4px' }}>Symbol</label>
            <select value={symbol} onChange={e => setSymbol(e.target.value)} style={selectStyle}>
              {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: '12px', color: '#6b6b8a', display: 'block', marginBottom: '4px' }}>Timeframe</label>
            <select value={timeframe} onChange={e => setTimeframe(e.target.value)} style={selectStyle}>
              {TIMEFRAMES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div style={{ marginTop: '18px' }}>
            <Button onClick={handleRun} disabled={loading} size="lg" icon={<Play size={16} />}>
              {loading ? 'Analyzing...' : 'Run Analysis'}
            </Button>
          </div>
        </div>
      </Card>

      {result && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: '20px', alignItems: 'start' }}>
            <ConfidenceScore score={result.setup_quality} direction={result.trade_direction} />
            <Card>
              <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '12px' }}>AI Explanation</h3>
              <p style={{ color: '#b8b8c8', fontSize: '14px', lineHeight: '1.7' }}>{result.ai_explanation}</p>
            </Card>
          </div>

          <Card>
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '16px' }}>Engine Results — {result.symbol} {result.timeframe}</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '12px' }}>
              {result.engines.map(e => <EngineResult key={e.engine_name} engine={e} />)}
            </div>
          </Card>

          {riskResult && (
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0' }}>Risk Check</h3>
                {riskResult.approved
                  ? <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#00d4a0', fontSize: '13px', fontWeight: 600 }}><CheckCircle size={16} /> APPROVED</div>
                  : <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#ff4757', fontSize: '13px', fontWeight: 600 }}><XCircle size={16} /> REJECTED — {riskResult.rejection_reason}</div>}
              </div>
              {riskResult.approved && (
                <div style={{ display: 'flex', gap: '20px', marginBottom: '16px', flexWrap: 'wrap' }}>
                  <div style={{ background: 'rgba(0,212,160,0.1)', border: '1px solid rgba(0,212,160,0.2)', borderRadius: '8px', padding: '12px 20px', textAlign: 'center' }}>
                    <div style={{ fontSize: '22px', fontWeight: 700, color: '#00d4a0', fontFamily: 'monospace' }}>{riskResult.position_size} lots</div>
                    <div style={{ fontSize: '12px', color: '#6b6b8a' }}>Position Size</div>
                  </div>
                  <div style={{ background: 'rgba(74,158,255,0.1)', border: '1px solid rgba(74,158,255,0.2)', borderRadius: '8px', padding: '12px 20px', textAlign: 'center' }}>
                    <div style={{ fontSize: '22px', fontWeight: 700, color: '#4a9eff', fontFamily: 'monospace' }}>${riskResult.risk_amount}</div>
                    <div style={{ fontSize: '12px', color: '#6b6b8a' }}>Risk Amount</div>
                  </div>
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {riskResult.checks.map(c => (
                  <div key={c.rule} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 12px', background: '#0a0a0f', borderRadius: '6px' }}>
                    {c.passed ? <CheckCircle size={14} color="#00d4a0" /> : <XCircle size={14} color="#ff4757" />}
                    <span style={{ fontSize: '13px', color: '#e8e8f0', flex: 1 }}>{c.rule}</span>
                    <span style={{ fontSize: '12px', color: '#6b6b8a', fontFamily: 'monospace' }}>{c.value}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
