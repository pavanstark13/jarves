'use client';

import { useState } from 'react';
import { Brain, Zap, TrendingUp, TrendingDown, AlertTriangle, Target, Shield, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

const BASE = '/api';

// ── mock trade data seeded with realistic SMC trades ──────────────────────────
const MOCK_TRADES = [
  { symbol:'EURUSD', direction:'LONG',  session:'LONDON',   result:'WIN',  r_multiple:2.1,  pnl:210, setup_quality:82, exit_reason:'TP_HIT',  strategy_tag:'SMC_OB',  entry_time:'2024-06-03T08:15:00', exit_time:'2024-06-03T10:45:00' },
  { symbol:'XAUUSD', direction:'SHORT', session:'NEW_YORK',  result:'LOSS', r_multiple:-1.0, pnl:-150,setup_quality:61, exit_reason:'SL_HIT',  strategy_tag:'SMC_FVG', entry_time:'2024-06-04T13:30:00', exit_time:'2024-06-04T14:10:00' },
  { symbol:'GBPUSD', direction:'LONG',  session:'LONDON',   result:'WIN',  r_multiple:1.8,  pnl:180, setup_quality:79, exit_reason:'TP_HIT',  strategy_tag:'SMC_OB',  entry_time:'2024-06-05T07:45:00', exit_time:'2024-06-05T09:30:00' },
  { symbol:'USDJPY', direction:'SHORT', session:'LONDON',   result:'WIN',  r_multiple:2.3,  pnl:230, setup_quality:88, exit_reason:'TP_HIT',  strategy_tag:'SMC_BOS', entry_time:'2024-06-06T08:00:00', exit_time:'2024-06-06T11:20:00' },
  { symbol:'EURUSD', direction:'LONG',  session:'NEW_YORK',  result:'LOSS', r_multiple:-1.0, pnl:-100,setup_quality:55, exit_reason:'SL_HIT',  strategy_tag:'SMC_FVG', entry_time:'2024-06-07T14:00:00', exit_time:'2024-06-07T14:45:00' },
  { symbol:'XAUUSD', direction:'LONG',  session:'LONDON',   result:'WIN',  r_multiple:3.1,  pnl:310, setup_quality:91, exit_reason:'TP_HIT',  strategy_tag:'SMC_OB',  entry_time:'2024-06-10T08:30:00', exit_time:'2024-06-10T12:00:00' },
  { symbol:'BTCUSD', direction:'LONG',  session:'NEW_YORK',  result:'LOSS', r_multiple:-1.0, pnl:-200,setup_quality:58, exit_reason:'SL_HIT',  strategy_tag:'SMC_FVG', entry_time:'2024-06-11T13:15:00', exit_time:'2024-06-11T14:00:00' },
  { symbol:'AUDUSD', direction:'SHORT', session:'ASIA',     result:'LOSS', r_multiple:-1.0, pnl:-75, setup_quality:52, exit_reason:'SL_HIT',  strategy_tag:'SMC_OB',  entry_time:'2024-06-12T02:00:00', exit_time:'2024-06-12T03:30:00' },
  { symbol:'GBPUSD', direction:'SHORT', session:'LONDON',   result:'WIN',  r_multiple:2.0,  pnl:200, setup_quality:85, exit_reason:'TP_HIT',  strategy_tag:'SMC_BOS', entry_time:'2024-06-13T07:30:00', exit_time:'2024-06-13T10:45:00' },
  { symbol:'EURUSD', direction:'LONG',  session:'LONDON',   result:'WIN',  r_multiple:1.9,  pnl:190, setup_quality:83, exit_reason:'TP_HIT',  strategy_tag:'SMC_OB',  entry_time:'2024-06-14T08:00:00', exit_time:'2024-06-14T10:30:00' },
  { symbol:'USDCHF', direction:'SHORT', session:'LONDON',   result:'WIN',  r_multiple:1.7,  pnl:170, setup_quality:76, exit_reason:'TP_HIT',  strategy_tag:'SMC_FVG', entry_time:'2024-06-17T07:45:00', exit_time:'2024-06-17T09:15:00' },
  { symbol:'XAUUSD', direction:'SHORT', session:'NEW_YORK',  result:'LOSS', r_multiple:-1.0, pnl:-150,setup_quality:63, exit_reason:'SL_HIT',  strategy_tag:'SMC_OB',  entry_time:'2024-06-18T13:00:00', exit_time:'2024-06-18T14:20:00' },
  { symbol:'USDJPY', direction:'LONG',  session:'LONDON',   result:'WIN',  r_multiple:2.5,  pnl:250, setup_quality:90, exit_reason:'TP_HIT',  strategy_tag:'SMC_BOS', entry_time:'2024-06-19T08:15:00', exit_time:'2024-06-19T12:00:00' },
  { symbol:'EURUSD', direction:'SHORT', session:'ASIA',     result:'LOSS', r_multiple:-1.0, pnl:-100,setup_quality:48, exit_reason:'SL_HIT',  strategy_tag:'SMC_FVG', entry_time:'2024-06-20T03:00:00', exit_time:'2024-06-20T04:15:00' },
  { symbol:'GBPUSD', direction:'LONG',  session:'LONDON',   result:'WIN',  r_multiple:2.2,  pnl:220, setup_quality:86, exit_reason:'TP_HIT',  strategy_tag:'SMC_OB',  entry_time:'2024-06-21T07:30:00', exit_time:'2024-06-21T11:45:00' },
];

const CARD: React.CSSProperties = {
  background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: '12px', padding: '20px',
};
const LABEL: React.CSSProperties = {
  fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase',
  color: '#7070a0', fontWeight: 500,
};
const SECTION_TITLE: React.CSSProperties = {
  fontSize: '13px', fontWeight: 700, color: '#f0f0ff',
  letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '16px',
};

type TabKey = 'overview' | 'pairs' | 'sessions' | 'silent' | 'strategy';

export default function AIInsightsPage() {
  const [tab, setTab] = useState<TabKey>('overview');
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);
  const [strategy, setStrategy] = useState<any>(null);
  const [silent, setSilent] = useState<any>(null);
  const [error, setError] = useState('');
  const [trades] = useState(MOCK_TRADES);

  const stats = computeStats(trades);

  async function runAnalysis() {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${BASE}/ai-insights/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trades, account_balance: 50000 }),
      });
      if (!res.ok) throw new Error(await res.text());
      setAnalysis(await res.json());
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  async function runStrategy() {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${BASE}/ai-insights/strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trades, account_balance: 50000 }),
      });
      if (!res.ok) throw new Error(await res.text());
      setStrategy(await res.json());
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  async function runSilent() {
    setLoading(true); setError('');
    try {
      const res = await fetch(`${BASE}/ai-insights/silent-periods`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trades, account_balance: 50000 }),
      });
      if (!res.ok) throw new Error(await res.text());
      setSilent(await res.json());
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }

  const tabs: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: 'overview',  label: 'Overview',        icon: <Brain size={14} /> },
    { key: 'pairs',     label: 'Pair Analysis',   icon: <TrendingUp size={14} /> },
    { key: 'sessions',  label: 'Session Intel',   icon: <Target size={14} /> },
    { key: 'silent',    label: 'Silent Periods',  icon: <AlertTriangle size={14} /> },
    { key: 'strategy',  label: 'My Strategy',     icon: <Shield size={14} /> },
  ];

  return (
    <div style={{ background: '#07071a', minHeight: '100vh', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'linear-gradient(135deg, #00e5cc, #4a9eff)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 20px rgba(0,229,204,0.3)' }}>
            <Brain size={20} color="#07071a" />
          </div>
          <div>
            <h1 style={{ fontSize: '20px', fontWeight: 800, color: '#f0f0ff', margin: 0, letterSpacing: '0.5px' }}>AI TRADE INTELLIGENCE</h1>
            <p style={{ ...LABEL, margin: 0 }}>Powered by Google Gemini · {trades.length} trades analyzed</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          {tab === 'overview' && <Button onClick={runAnalysis} disabled={loading} icon={loading ? <RefreshCw size={13} /> : <Brain size={13} />} variant="primary">
            {loading ? 'Analyzing…' : 'Run Full Analysis'}
          </Button>}
          {tab === 'strategy' && <Button onClick={runStrategy} disabled={loading} icon={loading ? <RefreshCw size={13} /> : <Zap size={13} />} variant="primary">
            {loading ? 'Generating…' : 'Generate My Strategy'}
          </Button>}
          {tab === 'silent' && <Button onClick={runSilent} disabled={loading} icon={loading ? <RefreshCw size={13} /> : <AlertTriangle size={13} />} variant="danger">
            {loading ? 'Analyzing…' : 'Find Silent Periods'}
          </Button>}
        </div>
      </div>

      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '12px' }}>
        {[
          { label: 'Win Rate',       value: `${stats.winRate.toFixed(1)}%`,       color: stats.winRate >= 60 ? '#00e5a0' : '#ff4466' },
          { label: 'Profit Factor',  value: stats.profitFactor.toFixed(2),         color: stats.profitFactor >= 1.5 ? '#00e5a0' : '#ff4466' },
          { label: 'Expectancy',     value: `${stats.expectancy.toFixed(2)}R`,     color: stats.expectancy >= 0 ? '#00e5a0' : '#ff4466' },
          { label: 'Net P&L',        value: `$${stats.netPnl.toFixed(0)}`,         color: stats.netPnl >= 0 ? '#00e5a0' : '#ff4466' },
          { label: 'Total Trades',   value: String(stats.total),                   color: '#f0f0ff' },
          { label: 'Best Pair',      value: stats.bestPair,                        color: '#00e5cc' },
          { label: 'Best Session',   value: stats.bestSession,                     color: '#00e5cc' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ ...CARD, padding: '14px 16px' }}>
            <div style={LABEL}>{label}</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color, fontFamily: 'monospace', marginTop: '4px' }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '0' }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            display: 'flex', alignItems: 'center', gap: '6px', padding: '10px 16px',
            background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', fontWeight: 600,
            color: tab === t.key ? '#00e5cc' : '#7070a0',
            borderBottom: tab === t.key ? '2px solid #00e5cc' : '2px solid transparent',
            marginBottom: '-1px', transition: 'all 0.2s',
          }}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      {error && (
        <div style={{ ...CARD, borderColor: 'rgba(255,68,102,0.3)', background: 'rgba(255,68,102,0.05)', color: '#ff4466', fontSize: '13px' }}>
          <AlertTriangle size={14} style={{ display: 'inline', marginRight: '8px' }} />
          {error}
          {error.includes('GOOGLE_API_KEY') && <span> — <a href="https://aistudio.google.com/app/apikey" target="_blank" style={{ color: '#00e5cc' }}>Get free key here</a></span>}
        </div>
      )}

      {/* ── TAB: OVERVIEW ── */}
      {tab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Charts row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
            <PairChart trades={trades} />
            <SessionChart trades={trades} />
            <DirectionChart trades={trades} />
          </div>

          {/* Quality analysis */}
          <SetupQualityChart trades={trades} />

          {/* AI analysis output */}
          {analysis ? (
            <AITextCard title="AI Full Analysis" text={analysis.ai_analysis} icon={<Brain size={14} />} />
          ) : (
            <div style={{ ...CARD, textAlign: 'center', padding: '40px' }}>
              <Brain size={40} color="#2a2a4a" style={{ display: 'block', margin: '0 auto 16px' }} />
              <div style={{ color: '#7070a0', fontSize: '14px', marginBottom: '12px' }}>
                Click "Run Full Analysis" to get AI-powered insights on your trading patterns
              </div>
              <div style={{ color: '#4a4a6a', fontSize: '12px' }}>
                Analyzes: winning patterns • losing patterns • best pairs • session intel • risk management • your edge
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB: PAIR ANALYSIS ── */}
      {tab === 'pairs' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <PairBreakdownTable trades={trades} />
          <PairChart trades={trades} large />
        </div>
      )}

      {/* ── TAB: SESSION INTEL ── */}
      {tab === 'sessions' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <SessionBreakdownTable trades={trades} />
          <SessionChart trades={trades} large />
        </div>
      )}

      {/* ── TAB: SILENT PERIODS ── */}
      {tab === 'silent' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <SilentPeriodStats trades={trades} />
          {silent ? (
            <AITextCard title="SILENCE PROTOCOL" text={silent.silence_protocol} icon={<AlertTriangle size={14} />} accentColor="#ff4466" />
          ) : (
            <div style={{ ...CARD, textAlign: 'center', padding: '40px' }}>
              <AlertTriangle size={40} color="#2a2a4a" style={{ display: 'block', margin: '0 auto 16px' }} />
              <div style={{ color: '#7070a0', fontSize: '14px' }}>
                Click "Find Silent Periods" to identify exactly when you should NOT be trading
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB: MY STRATEGY ── */}
      {tab === 'strategy' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
            <StatHighlight label="Your Best Pair" value={stats.bestPair} sub="Most profitable instrument" color="#00e5cc" />
            <StatHighlight label="Your Best Session" value={stats.bestSession} sub="Highest win rate window" color="#00e5a0" />
            <StatHighlight label="Your Best Direction" value={stats.bestDirection} sub="Long or Short bias" color="#4a9eff" />
          </div>
          {strategy ? (
            <AITextCard title="PERSONALIZED STRATEGY" text={strategy.personalized_strategy} icon={<Shield size={14} />} accentColor="#00e5cc" />
          ) : (
            <div style={{ ...CARD, textAlign: 'center', padding: '40px' }}>
              <Shield size={40} color="#2a2a4a" style={{ display: 'block', margin: '0 auto 16px' }} />
              <div style={{ color: '#7070a0', fontSize: '14px', marginBottom: '8px' }}>
                Click "Generate My Strategy" for a personalized trading plan
              </div>
              <div style={{ color: '#4a4a6a', fontSize: '12px' }}>
                Based on your actual trade data: approved pairs • banned pairs • entry checklist • position sizing • daily limits
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── sub-components ────────────────────────────────────────────────────────────

function AITextCard({ title, text, icon, accentColor = '#00e5cc' }: { title: string; text: string; icon: React.ReactNode; accentColor?: string }) {
  return (
    <div style={{ background: '#0d0d22', border: `1px solid ${accentColor}22`, borderRadius: '12px', padding: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px', color: accentColor }}>
        {icon}
        <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase' }}>{title}</span>
      </div>
      <div style={{ color: '#c0c0e0', fontSize: '14px', lineHeight: '1.8', whiteSpace: 'pre-wrap' }}>
        {text.split('\n').map((line, i) => {
          if (line.startsWith('## ')) return <h3 key={i} style={{ color: accentColor, fontSize: '13px', fontWeight: 700, letterSpacing: '1px', marginTop: '20px', marginBottom: '8px' }}>{line.slice(3)}</h3>;
          if (line.startsWith('- ') || line.match(/^\d+\./)) return <div key={i} style={{ paddingLeft: '16px', marginBottom: '4px', color: '#d0d0f0' }}>{line}</div>;
          if (line.trim() === '') return <div key={i} style={{ height: '8px' }} />;
          return <div key={i} style={{ marginBottom: '4px' }}>{line}</div>;
        })}
      </div>
    </div>
  );
}

function StatHighlight({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div style={{ background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '24px', textAlign: 'center' }}>
      <div style={{ fontSize: '10px', letterSpacing: '1.5px', textTransform: 'uppercase', color: '#7070a0', marginBottom: '12px' }}>{label}</div>
      <div style={{ fontSize: '32px', fontWeight: 800, color, fontFamily: 'monospace' }}>{value}</div>
      <div style={{ fontSize: '12px', color: '#7070a0', marginTop: '8px' }}>{sub}</div>
    </div>
  );
}

function PairChart({ trades, large }: { trades: any[]; large?: boolean }) {
  const byPair: Record<string, { wins: number; losses: number; pnl: number }> = {};
  trades.forEach(t => {
    if (!byPair[t.symbol]) byPair[t.symbol] = { wins: 0, losses: 0, pnl: 0 };
    if (t.result === 'WIN') byPair[t.symbol].wins++;
    else byPair[t.symbol].losses++;
    byPair[t.symbol].pnl += t.pnl;
  });
  const data = Object.entries(byPair).map(([sym, d]) => ({
    name: sym, pnl: Math.round(d.pnl), wr: Math.round(d.wins / (d.wins + d.losses) * 100),
  })).sort((a, b) => b.pnl - a.pnl);

  return (
    <div style={{ background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '20px', gridColumn: large ? '1/-1' : undefined }}>
      <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '2px', color: '#7070a0', textTransform: 'uppercase', marginBottom: '16px' }}>P&L by Pair</div>
      <ResponsiveContainer width="100%" height={large ? 280 : 180}>
        <BarChart data={data}>
          <CartesianGrid stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="name" tick={{ fill: '#7070a0', fontSize: 11 }} />
          <YAxis tick={{ fill: '#7070a0', fontSize: 10 }} tickFormatter={v => `$${v}`} />
          <Tooltip contentStyle={{ background: '#12122a', border: '1px solid #2a2a4a', borderRadius: '8px', color: '#f0f0ff' }} formatter={(v: number) => [`$${v}`, 'P&L']} />
          <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
            {data.map((d, i) => <Cell key={i} fill={d.pnl >= 0 ? '#00e5a0' : '#ff4466'} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function SessionChart({ trades, large }: { trades: any[]; large?: boolean }) {
  const bySess: Record<string, { wins: number; total: number; pnl: number }> = {};
  trades.forEach(t => {
    const s = t.session || 'UNKNOWN';
    if (!bySess[s]) bySess[s] = { wins: 0, total: 0, pnl: 0 };
    bySess[s].total++;
    if (t.result === 'WIN') bySess[s].wins++;
    bySess[s].pnl += t.pnl;
  });
  const data = Object.entries(bySess).map(([s, d]) => ({
    name: s.replace('_', ' '), wr: Math.round(d.wins / d.total * 100), pnl: Math.round(d.pnl),
  }));

  return (
    <div style={{ background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '20px', gridColumn: large ? '1/-1' : undefined }}>
      <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '2px', color: '#7070a0', textTransform: 'uppercase', marginBottom: '16px' }}>Win Rate by Session</div>
      <ResponsiveContainer width="100%" height={large ? 280 : 180}>
        <BarChart data={data}>
          <CartesianGrid stroke="rgba(255,255,255,0.04)" />
          <XAxis dataKey="name" tick={{ fill: '#7070a0', fontSize: 11 }} />
          <YAxis tick={{ fill: '#7070a0', fontSize: 10 }} tickFormatter={v => `${v}%`} domain={[0, 100]} />
          <Tooltip contentStyle={{ background: '#12122a', border: '1px solid #2a2a4a', borderRadius: '8px', color: '#f0f0ff' }} formatter={(v: number) => [`${v}%`, 'Win Rate']} />
          <Bar dataKey="wr" radius={[4, 4, 0, 0]}>
            {data.map((d, i) => <Cell key={i} fill={d.wr >= 60 ? '#00e5cc' : d.wr >= 40 ? '#f0c040' : '#ff4466'} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function DirectionChart({ trades }: { trades: any[] }) {
  const longs  = trades.filter(t => t.direction === 'LONG');
  const shorts = trades.filter(t => t.direction === 'SHORT');
  const lwins  = longs.filter(t => t.result === 'WIN');
  const swins  = shorts.filter(t => t.result === 'WIN');
  const data = [
    { name: 'LONG',  wr: longs.length  ? Math.round(lwins.length  / longs.length  * 100) : 0, pnl: Math.round(longs.reduce((s, t)  => s + t.pnl, 0)) },
    { name: 'SHORT', wr: shorts.length ? Math.round(swins.length / shorts.length * 100) : 0, pnl: Math.round(shorts.reduce((s, t) => s + t.pnl, 0)) },
  ];
  return (
    <div style={{ background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '20px' }}>
      <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '2px', color: '#7070a0', textTransform: 'uppercase', marginBottom: '16px' }}>Long vs Short</div>
      <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', marginBottom: '20px' }}>
        {data.map(d => (
          <div key={d.name} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '28px', fontWeight: 800, color: d.name === 'LONG' ? '#00e5a0' : '#ff4466', fontFamily: 'monospace' }}>{d.wr}%</div>
            <div style={{ fontSize: '10px', color: '#7070a0', letterSpacing: '1px' }}>{d.name} WIN RATE</div>
            <div style={{ fontSize: '13px', color: d.pnl >= 0 ? '#00e5a0' : '#ff4466', fontFamily: 'monospace', marginTop: '4px' }}>${d.pnl}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '4px', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
        <div style={{ flex: longs.length, background: '#00e5a0', opacity: 0.8 }} />
        <div style={{ flex: shorts.length, background: '#ff4466', opacity: 0.8 }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px' }}>
        <span style={{ fontSize: '10px', color: '#00e5a0' }}>LONG {longs.length} trades</span>
        <span style={{ fontSize: '10px', color: '#ff4466' }}>SHORT {shorts.length} trades</span>
      </div>
    </div>
  );
}

function SetupQualityChart({ trades }: { trades: any[] }) {
  const buckets = [
    { label: 'LOW (<60)', min: 0,  max: 60,  color: '#ff4466' },
    { label: 'MID (60-80)', min: 60, max: 80, color: '#f0c040' },
    { label: 'HIGH (80+)', min: 80, max: 101, color: '#00e5a0' },
  ];
  const data = buckets.map(b => {
    const grp = trades.filter(t => t.setup_quality >= b.min && t.setup_quality < b.max);
    const wins = grp.filter(t => t.result === 'WIN');
    return {
      name: b.label, trades: grp.length, color: b.color,
      wr: grp.length ? Math.round(wins.length / grp.length * 100) : 0,
      pnl: Math.round(grp.reduce((s, t) => s + t.pnl, 0)),
    };
  });

  return (
    <div style={{ background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '20px' }}>
      <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '2px', color: '#7070a0', textTransform: 'uppercase', marginBottom: '16px' }}>Setup Quality vs Results</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
        {data.map(d => (
          <div key={d.name} style={{ background: '#10102a', borderRadius: '10px', padding: '16px', borderLeft: `3px solid ${d.color}` }}>
            <div style={{ fontSize: '10px', color: '#7070a0', letterSpacing: '1px', marginBottom: '8px' }}>{d.name}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div>
                <div style={{ fontSize: '26px', fontWeight: 700, color: d.color, fontFamily: 'monospace' }}>{d.wr}%</div>
                <div style={{ fontSize: '11px', color: '#7070a0' }}>{d.trades} trades</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '15px', fontWeight: 600, color: d.pnl >= 0 ? '#00e5a0' : '#ff4466', fontFamily: 'monospace' }}>${d.pnl}</div>
                <div style={{ fontSize: '10px', color: '#7070a0' }}>net P&L</div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: '12px', padding: '10px 14px', background: '#10102a', borderRadius: '8px', fontSize: '12px', color: '#7070a0' }}>
        💡 Only take trades with setup quality ≥ 80 — win rate jumps significantly in HIGH bucket
      </div>
    </div>
  );
}

function PairBreakdownTable({ trades }: { trades: any[] }) {
  const byPair: Record<string, any[]> = {};
  trades.forEach(t => { (byPair[t.symbol] = byPair[t.symbol] || []).push(t); });
  const rows = Object.entries(byPair).map(([sym, ts]) => {
    const wins   = ts.filter(t => t.result === 'WIN');
    const losses = ts.filter(t => t.result === 'LOSS');
    const pnl    = ts.reduce((s, t) => s + t.pnl, 0);
    return { sym, total: ts.length, wins: wins.length, losses: losses.length, wr: wins.length / ts.length * 100, pnl };
  }).sort((a, b) => b.pnl - a.pnl);

  return (
    <div style={{ background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '20px' }}>
      <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '2px', color: '#7070a0', textTransform: 'uppercase', marginBottom: '16px' }}>Pair Performance Breakdown</div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
        <thead>
          <tr style={{ color: '#4a4a6a', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            {['Rank', 'Pair', 'Trades', 'Wins', 'Losses', 'Win Rate', 'Net P&L', 'Verdict'].map(h => (
              <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 500, fontSize: '10px', letterSpacing: '1px', textTransform: 'uppercase' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.sym} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
              <td style={{ padding: '10px 12px', color: '#4a4a6a', fontFamily: 'monospace' }}>#{i + 1}</td>
              <td style={{ padding: '10px 12px', fontWeight: 700, color: '#f0f0ff', letterSpacing: '0.5px' }}>{r.sym}</td>
              <td style={{ padding: '10px 12px', color: '#c0c0e0' }}>{r.total}</td>
              <td style={{ padding: '10px 12px', color: '#00e5a0' }}>{r.wins}</td>
              <td style={{ padding: '10px 12px', color: '#ff4466' }}>{r.losses}</td>
              <td style={{ padding: '10px 12px', color: r.wr >= 60 ? '#00e5a0' : r.wr >= 40 ? '#f0c040' : '#ff4466', fontWeight: 700, fontFamily: 'monospace' }}>{r.wr.toFixed(1)}%</td>
              <td style={{ padding: '10px 12px', color: r.pnl >= 0 ? '#00e5a0' : '#ff4466', fontFamily: 'monospace', fontWeight: 700 }}>${r.pnl.toFixed(0)}</td>
              <td style={{ padding: '10px 12px' }}>
                <Badge variant={r.pnl > 0 && r.wr >= 60 ? 'green' : r.pnl > 0 ? 'blue' : 'red'}>
                  {r.pnl > 0 && r.wr >= 60 ? 'KEEP' : r.pnl > 0 ? 'WATCH' : 'AVOID'}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SessionBreakdownTable({ trades }: { trades: any[] }) {
  const bySess: Record<string, any[]> = {};
  trades.forEach(t => { const s = t.session || 'UNKNOWN'; (bySess[s] = bySess[s] || []).push(t); });
  const rows = Object.entries(bySess).map(([sess, ts]) => {
    const wins = ts.filter(t => t.result === 'WIN');
    const pnl  = ts.reduce((s, t) => s + t.pnl, 0);
    return { sess, total: ts.length, wins: wins.length, wr: wins.length / ts.length * 100, pnl };
  }).sort((a, b) => b.pnl - a.pnl);

  const sessionUTC: Record<string, string> = {
    LONDON: '07:00 – 16:00 UTC', NEW_YORK: '13:00 – 22:00 UTC',
    ASIA: '00:00 – 09:00 UTC', OVERLAP: '13:00 – 16:00 UTC',
  };

  return (
    <div style={{ background: '#0d0d22', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px', padding: '20px' }}>
      <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '2px', color: '#7070a0', textTransform: 'uppercase', marginBottom: '16px' }}>Session Performance</div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
        <thead>
          <tr style={{ color: '#4a4a6a', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            {['Session', 'UTC Hours', 'Trades', 'Wins', 'Win Rate', 'Net P&L', 'Status'].map(h => (
              <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 500, fontSize: '10px', letterSpacing: '1px', textTransform: 'uppercase' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.sess} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
              <td style={{ padding: '10px 12px', fontWeight: 700, color: '#f0f0ff' }}>{r.sess.replace('_', ' ')}</td>
              <td style={{ padding: '10px 12px', color: '#7070a0', fontSize: '12px' }}>{sessionUTC[r.sess] || '—'}</td>
              <td style={{ padding: '10px 12px', color: '#c0c0e0' }}>{r.total}</td>
              <td style={{ padding: '10px 12px', color: '#00e5a0' }}>{r.wins}</td>
              <td style={{ padding: '10px 12px', color: r.wr >= 60 ? '#00e5a0' : r.wr >= 40 ? '#f0c040' : '#ff4466', fontWeight: 700, fontFamily: 'monospace' }}>{r.wr.toFixed(1)}%</td>
              <td style={{ padding: '10px 12px', color: r.pnl >= 0 ? '#00e5a0' : '#ff4466', fontFamily: 'monospace', fontWeight: 700 }}>${r.pnl.toFixed(0)}</td>
              <td style={{ padding: '10px 12px' }}>
                <Badge variant={r.wr >= 60 && r.pnl > 0 ? 'green' : r.pnl > 0 ? 'blue' : 'red'}>
                  {r.wr >= 60 && r.pnl > 0 ? 'TRADE' : r.pnl > 0 ? 'CAUTION' : 'AVOID'}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SilentPeriodStats({ trades }: { trades: any[] }) {
  const bySess: Record<string, any[]> = {};
  trades.forEach(t => { const s = t.session || 'UNKNOWN'; (bySess[s] = bySess[s] || []).push(t); });
  const dangerSessions = Object.entries(bySess)
    .filter(([, ts]) => { const w = ts.filter(t => t.result === 'WIN'); return w.length / ts.length < 0.4; })
    .map(([s]) => s);

  const byPair: Record<string, any[]> = {};
  trades.forEach(t => { (byPair[t.symbol] = byPair[t.symbol] || []).push(t); });
  const losingPairs = Object.entries(byPair)
    .filter(([, ts]) => ts.reduce((s, t) => s + t.pnl, 0) < 0)
    .map(([s]) => s);

  const lowQLoss = trades.filter(t => t.setup_quality < 65 && t.result === 'LOSS').length;
  const lowQTotal = trades.filter(t => t.setup_quality < 65).length;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
      <div style={{ background: '#0d0d22', border: '1px solid rgba(255,68,102,0.2)', borderRadius: '12px', padding: '20px' }}>
        <div style={{ fontSize: '10px', letterSpacing: '1.5px', color: '#ff4466', marginBottom: '12px', textTransform: 'uppercase', fontWeight: 700 }}>⚠ Dangerous Sessions</div>
        {dangerSessions.length > 0 ? dangerSessions.map(s => (
          <div key={s} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#ff4466' }} />
            <span style={{ color: '#f0f0ff', fontSize: '14px', fontWeight: 600 }}>{s.replace('_', ' ')}</span>
            <span style={{ color: '#7070a0', fontSize: '12px' }}>— avoid</span>
          </div>
        )) : <div style={{ color: '#00e5a0', fontSize: '13px' }}>All sessions profitable ✓</div>}
      </div>
      <div style={{ background: '#0d0d22', border: '1px solid rgba(255,68,102,0.2)', borderRadius: '12px', padding: '20px' }}>
        <div style={{ fontSize: '10px', letterSpacing: '1.5px', color: '#ff4466', marginBottom: '12px', textTransform: 'uppercase', fontWeight: 700 }}>⚠ Losing Pairs</div>
        {losingPairs.length > 0 ? losingPairs.map(s => (
          <div key={s} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#ff4466' }} />
            <span style={{ color: '#f0f0ff', fontSize: '14px', fontWeight: 600 }}>{s}</span>
            <span style={{ color: '#7070a0', fontSize: '12px' }}>— negative P&L</span>
          </div>
        )) : <div style={{ color: '#00e5a0', fontSize: '13px' }}>All pairs profitable ✓</div>}
      </div>
      <div style={{ background: '#0d0d22', border: '1px solid rgba(255,68,102,0.2)', borderRadius: '12px', padding: '20px' }}>
        <div style={{ fontSize: '10px', letterSpacing: '1.5px', color: '#ff4466', marginBottom: '12px', textTransform: 'uppercase', fontWeight: 700 }}>⚠ Low Quality Trades</div>
        <div style={{ fontSize: '32px', fontWeight: 800, color: '#ff4466', fontFamily: 'monospace' }}>
          {lowQTotal > 0 ? `${Math.round(lowQLoss / lowQTotal * 100)}%` : '0%'}
        </div>
        <div style={{ fontSize: '12px', color: '#7070a0', marginTop: '4px' }}>loss rate on setups below 65 quality ({lowQTotal} trades)</div>
        <div style={{ marginTop: '12px', fontSize: '12px', color: '#f0c040' }}>→ Skip all trades under quality 70</div>
      </div>
    </div>
  );
}

// ── stats calculation ─────────────────────────────────────────────────────────
function computeStats(trades: any[]) {
  const wins   = trades.filter(t => t.result === 'WIN');
  const losses = trades.filter(t => t.result === 'LOSS');
  const gp     = wins.reduce((s, t) => s + t.pnl, 0);
  const gl     = Math.abs(losses.reduce((s, t) => s + t.pnl, 0));
  const wr     = trades.length ? wins.length / trades.length * 100 : 0;
  const pf     = gl > 0 ? gp / gl : 0;
  const avgWR  = wins.length ? wins.reduce((s, t) => s + t.r_multiple, 0) / wins.length : 0;
  const avgLR  = losses.length ? Math.abs(losses.reduce((s, t) => s + t.r_multiple, 0) / losses.length) : 0;
  const exp    = (wr / 100) * avgWR - (1 - wr / 100) * avgLR;

  const byPair: Record<string, number> = {};
  trades.forEach(t => { byPair[t.symbol] = (byPair[t.symbol] || 0) + t.pnl; });
  const bestPair = Object.entries(byPair).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '—';

  const bySess: Record<string, number> = {};
  trades.forEach(t => { bySess[t.session] = (bySess[t.session] || 0) + t.pnl; });
  const bestSession = Object.entries(bySess).sort((a, b) => b[1] - a[1])[0]?.[0]?.replace('_', ' ') ?? '—';

  const longPnl  = trades.filter(t => t.direction === 'LONG').reduce((s, t) => s + t.pnl, 0);
  const shortPnl = trades.filter(t => t.direction === 'SHORT').reduce((s, t) => s + t.pnl, 0);
  const bestDirection = longPnl >= shortPnl ? 'LONG' : 'SHORT';

  return { total: trades.length, winRate: wr, profitFactor: pf, expectancy: exp, netPnl: gp - gl, bestPair, bestSession, bestDirection };
}
