'use client';

import { useState, useEffect } from 'react';
import { api, BacktestRun, BacktestRunDetail, BacktestTradeItem } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, ReferenceLine } from 'recharts';
import { FlaskConical, Play, RefreshCw, TrendingUp, TrendingDown, Target, Activity } from 'lucide-react';

const SYMBOLS = ['ALL', 'EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF', 'AUDUSD', 'USDCAD', 'XAUUSD', 'BTCUSD'];

function StatCard({ label, value, sub, positive }: { label: string; value: string; sub?: string; positive?: boolean }) {
  return (
    <div style={{ background: '#12121e', border: '1px solid #1e1e2e', borderRadius: '12px', padding: '16px' }}>
      <div style={{ fontSize: '12px', color: '#6b6b8a', marginBottom: '6px' }}>{label}</div>
      <div style={{ fontSize: '22px', fontWeight: 700, color: positive === undefined ? '#e8e8f0' : positive ? '#00d4a0' : '#ff4757' }}>{value}</div>
      {sub && <div style={{ fontSize: '12px', color: '#6b6b8a', marginTop: '4px' }}>{sub}</div>}
    </div>
  );
}

export default function BacktestPage() {
  const [symbol, setSymbol] = useState('EURUSD');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [balance, setBalance] = useState('50000');
  const [runs, setRuns] = useState<BacktestRun[]>([]);
  const [selected, setSelected] = useState<BacktestRunDetail | null>(null);
  const [trades, setTrades] = useState<BacktestTradeItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [tradeFilter, setTradeFilter] = useState<string | undefined>(undefined);

  useEffect(() => { loadRuns(); }, []);

  async function loadRuns() {
    try { setRuns(await api.getBacktestRuns()); } catch {}
  }

  async function startBacktest() {
    setLoading(true);
    try {
      const r = await api.runBacktest({ symbol, start_date: startDate, end_date: endDate, initial_balance: parseFloat(balance) });
      await new Promise(res => setTimeout(res, 1000));
      await loadRuns();
      // Poll until complete
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        await loadRuns();
        const run = (await api.getBacktestRuns()).find(r2 => r2.run_id === r.run_id);
        if (!run || run.status === 'COMPLETED' || run.status === 'FAILED' || attempts > 60) {
          clearInterval(poll);
          setLoading(false);
          if (run && run.status === 'COMPLETED') {
            await selectRun(r.run_id);
          }
        }
      }, 3000);
    } catch (e) {
      setLoading(false);
      alert('Backtest failed: ' + e);
    }
  }

  async function selectRun(runId: string) {
    try {
      const detail = await api.getBacktestRun(runId);
      setSelected(detail);
      const t = await api.getBacktestTrades(runId, 1, tradeFilter);
      setTrades(t.trades);
    } catch {}
  }

  async function loadTrades(runId: string, filter?: string) {
    try {
      const t = await api.getBacktestTrades(runId, 1, filter);
      setTrades(t.trades);
      setTradeFilter(filter);
    } catch {}
  }

  const card = { background: '#12121e', border: '1px solid #1e1e2e', borderRadius: '12px', padding: '20px' };
  const inp = {
    background: '#0d0d15', border: '1px solid #2a2a3e', borderRadius: '8px',
    color: '#e8e8f0', padding: '8px 12px', fontSize: '14px', width: '100%', outline: 'none',
  };
  const label = { fontSize: '12px', color: '#6b6b8a', marginBottom: '6px', display: 'block' };

  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
        <FlaskConical size={24} color="#4a9eff" />
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#e8e8f0', margin: 0 }}>Backtesting</h1>
          <p style={{ fontSize: '13px', color: '#6b6b8a', margin: 0 }}>Simulate SMC strategy on historical data</p>
        </div>
      </div>

      {/* Config */}
      <div style={{ ...card, marginBottom: '20px' }}>
        <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '16px' }}>Configure Backtest</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px', alignItems: 'end' }}>
          <div>
            <label style={label}>Symbol</label>
            <select value={symbol} onChange={e => setSymbol(e.target.value)} style={inp}>
              {SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label style={label}>Start Date</label>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={inp} />
          </div>
          <div>
            <label style={label}>End Date</label>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} style={inp} />
          </div>
          <div>
            <label style={label}>Initial Balance ($)</label>
            <input type="number" value={balance} onChange={e => setBalance(e.target.value)} style={inp} />
          </div>
          <Button onClick={startBacktest} disabled={loading} icon={loading ? <RefreshCw size={14} /> : <Play size={14} />}>
            {loading ? 'Running…' : 'Run Backtest'}
          </Button>
        </div>
      </div>

      {/* Runs list */}
      {runs.length > 0 && (
        <div style={{ ...card, marginBottom: '20px' }}>
          <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '12px' }}>Recent Runs</h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ color: '#6b6b8a', borderBottom: '1px solid #1e1e2e' }}>
                  {['ID', 'Symbol', 'Status', 'Trades', 'Win Rate', 'Total P&L', 'Started', ''].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {runs.map(r => (
                  <tr key={r.run_id} style={{ borderBottom: '1px solid #1a1a28', color: '#c0c0d0' }}>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: '#4a9eff' }}>{r.run_id}</td>
                    <td style={{ padding: '8px 12px' }}>{r.symbol}</td>
                    <td style={{ padding: '8px 12px' }}>
                      <Badge variant={r.status === 'COMPLETED' ? 'green' : r.status === 'FAILED' ? 'red' : 'blue'}>
                        {r.status}
                      </Badge>
                    </td>
                    <td style={{ padding: '8px 12px' }}>{r.total_trades ?? '—'}</td>
                    <td style={{ padding: '8px 12px', color: (r.win_rate ?? 0) >= 70 ? '#00d4a0' : '#ff4757' }}>
                      {r.win_rate != null ? `${r.win_rate.toFixed(1)}%` : '—'}
                    </td>
                    <td style={{ padding: '8px 12px', color: (r.total_pnl ?? 0) >= 0 ? '#00d4a0' : '#ff4757' }}>
                      {r.total_pnl != null ? `$${r.total_pnl.toLocaleString()}` : '—'}
                    </td>
                    <td style={{ padding: '8px 12px', color: '#6b6b8a' }}>{r.started_at?.slice(0, 16)}</td>
                    <td style={{ padding: '8px 12px' }}>
                      {r.status === 'COMPLETED' && (
                        <Button variant="secondary" size="sm" onClick={() => selectRun(r.run_id)}>View</Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Selected run detail */}
      {selected && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '16px', marginBottom: '20px' }}>
            <StatCard label="Win Rate" value={`${selected.win_rate?.toFixed(1) ?? 0}%`} positive={(selected.win_rate ?? 0) >= 65} />
            <StatCard label="Profit Factor" value={selected.profit_factor?.toFixed(2) ?? '0'} positive={(selected.profit_factor ?? 0) > 1} />
            <StatCard label="Total P&L" value={`$${selected.total_pnl?.toLocaleString() ?? 0}`} positive={(selected.total_pnl ?? 0) >= 0} />
            <StatCard label="Expectancy" value={`${selected.expectancy_r?.toFixed(3) ?? 0}R`} positive={(selected.expectancy_r ?? 0) > 0} />
            <StatCard label="Max Drawdown" value={`${selected.max_drawdown_pct?.toFixed(1) ?? 0}%`} positive={(selected.max_drawdown_pct ?? 0) < 10} />
          </div>

          {selected.equity_curve?.length > 1 && (
            <div style={{ ...card, marginBottom: '20px' }}>
              <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '16px' }}>Equity Curve</h2>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={selected.equity_curve}>
                  <CartesianGrid stroke="#1e1e2e" />
                  <XAxis dataKey="timestamp" tick={{ fill: '#6b6b8a', fontSize: 11 }} tickFormatter={t => t?.slice(5, 10)} />
                  <YAxis tick={{ fill: '#6b6b8a', fontSize: 11 }} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} />
                  <Tooltip contentStyle={{ background: '#12121e', border: '1px solid #2a2a3e', borderRadius: '8px', color: '#e8e8f0' }}
                    formatter={(v: number) => [`$${v.toLocaleString()}`, 'Equity']} />
                  <ReferenceLine y={selected.initial_balance} stroke="#6b6b8a" strokeDasharray="4 4" />
                  <Line type="monotone" dataKey="equity" stroke="#4a9eff" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Trades table */}
          <div style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', margin: 0 }}>
                Trades ({selected.total_trades})
              </h2>
              <div style={{ display: 'flex', gap: '8px' }}>
                {[undefined, 'WIN', 'LOSS'].map(f => (
                  <Button key={String(f)} variant={tradeFilter === f ? 'primary' : 'ghost'} size="sm"
                    onClick={() => loadTrades(selected.run_id, f)}>
                    {f ?? 'All'}
                  </Button>
                ))}
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                <thead>
                  <tr style={{ color: '#6b6b8a', borderBottom: '1px solid #1e1e2e' }}>
                    {['Symbol', 'Dir', 'Entry Time', 'Exit', 'Entry', 'Exit Price', 'R', 'P&L', 'Session', 'Result'].map(h => (
                      <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 500 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #1a1a28', color: '#c0c0d0' }}>
                      <td style={{ padding: '7px 10px' }}>{t.symbol}</td>
                      <td style={{ padding: '7px 10px', color: t.direction === 'LONG' ? '#00d4a0' : '#ff4757' }}>{t.direction}</td>
                      <td style={{ padding: '7px 10px', color: '#6b6b8a' }}>{t.entry_time?.slice(0, 16)}</td>
                      <td style={{ padding: '7px 10px', color: '#6b6b8a' }}>{t.exit_time?.slice(0, 16)}</td>
                      <td style={{ padding: '7px 10px' }}>{t.entry_price?.toFixed(5)}</td>
                      <td style={{ padding: '7px 10px' }}>{t.exit_price?.toFixed(5)}</td>
                      <td style={{ padding: '7px 10px', color: t.r_multiple >= 0 ? '#00d4a0' : '#ff4757' }}>{t.r_multiple?.toFixed(2)}R</td>
                      <td style={{ padding: '7px 10px', color: t.pnl_usd >= 0 ? '#00d4a0' : '#ff4757' }}>${t.pnl_usd?.toFixed(0)}</td>
                      <td style={{ padding: '7px 10px', color: '#6b6b8a' }}>{t.session}</td>
                      <td style={{ padding: '7px 10px' }}>
                        <Badge variant={t.result === 'WIN' ? 'green' : t.result === 'LOSS' ? 'red' : 'blue'}>{t.result}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
