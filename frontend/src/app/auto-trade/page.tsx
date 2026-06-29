'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, ScannerStatus, OandaPosition, OandaAccount, ScannerSignalItem } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Bot, Power, RefreshCw, TrendingUp, TrendingDown, AlertCircle, Zap } from 'lucide-react';

function AccountCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div style={{ background: '#12121e', border: '1px solid #1e1e2e', borderRadius: '12px', padding: '20px', flex: 1 }}>
      <div style={{ fontSize: '12px', color: '#6b6b8a', marginBottom: '6px' }}>{label}</div>
      <div style={{ fontSize: '26px', fontWeight: 700, color: color ?? '#e8e8f0' }}>{value}</div>
      {sub && <div style={{ fontSize: '12px', color: '#6b6b8a', marginTop: '4px' }}>{sub}</div>}
    </div>
  );
}

function statusColor(status: string): 'green' | 'red' | 'blue' {
  if (status === 'PLACED') return 'green';
  if (status === 'FAILED') return 'red';
  return 'blue';
}

export default function AutoTradePage() {
  const [status, setStatus]     = useState<ScannerStatus | null>(null);
  const [positions, setPositions] = useState<OandaPosition[]>([]);
  const [account, setAccount]   = useState<OandaAccount | null>(null);
  const [loading, setLoading]   = useState(false);
  const [toggling, setToggling] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [oandaError, setOandaError] = useState('');
  const [countdown, setCountdown] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [st, pos] = await Promise.allSettled([
        api.getScannerStatus(),
        api.getOpenPositions(),
      ]);
      if (st.status === 'fulfilled') setStatus(st.value);
      if (pos.status === 'fulfilled') setPositions(pos.value);

      // Account is optional (needs OANDA keys)
      try {
        setAccount(await api.getOandaAccount());
        setOandaError('');
      } catch (e: any) {
        setOandaError(e.message ?? 'OANDA not configured');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { const t = setInterval(refresh, 15_000); return () => clearInterval(t); }, [refresh]);

  // Countdown to next scan
  useEffect(() => {
    if (!status?.next_scan_at) return;
    const tick = () => {
      const diff = new Date(status.next_scan_at).getTime() - Date.now();
      if (diff <= 0) { setCountdown('now'); return; }
      const m = Math.floor(diff / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setCountdown(`${m}m ${s}s`);
    };
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [status?.next_scan_at]);

  async function toggle() {
    if (!status) return;
    setToggling(true);
    try {
      await api.toggleScanner(!status.enabled);
      await refresh();
    } finally { setToggling(false); }
  }

  async function manualScan() {
    setScanning(true);
    try {
      const r = await api.triggerScan();
      alert(`Scan complete. ${r.signals_fired} signal(s) fired.`);
      await refresh();
    } catch (e: any) {
      alert('Scan failed: ' + e.message);
    } finally { setScanning(false); }
  }

  async function closePos(symbol: string) {
    if (!confirm(`Close all ${symbol} positions?`)) return;
    try {
      await api.closePosition(symbol);
      await refresh();
    } catch (e: any) {
      alert('Close failed: ' + e.message);
    }
  }

  const card = { background: '#12121e', border: '1px solid #1e1e2e', borderRadius: '12px', padding: '20px' };
  const signals: ScannerSignalItem[] = status?.signals_feed ?? [];

  return (
    <div style={{ padding: '24px', maxWidth: '1400px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Bot size={24} color="#4a9eff" />
          <div>
            <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#e8e8f0', margin: 0 }}>Auto Trade</h1>
            <p style={{ fontSize: '13px', color: '#6b6b8a', margin: 0 }}>SMC strategy auto-executes on OANDA Practice</p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <Button variant="ghost" size="sm" onClick={refresh} disabled={loading} icon={<RefreshCw size={14} />}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </Button>
          <Button variant="secondary" size="sm" onClick={manualScan} disabled={scanning} icon={<Zap size={14} />}>
            {scanning ? 'Scanning…' : 'Manual Scan'}
          </Button>
          <Button
            variant={status?.enabled ? 'danger' : 'primary'}
            size="sm"
            onClick={toggle}
            disabled={toggling}
            icon={<Power size={14} />}
          >
            {toggling ? '…' : status?.enabled ? 'Disable Scanner' : 'Enable Scanner'}
          </Button>
        </div>
      </div>

      {/* Scanner status bar */}
      <div style={{ ...card, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '32px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '10px', height: '10px', borderRadius: '50%',
            background: status?.enabled ? '#00d4a0' : '#6b6b8a',
            boxShadow: status?.enabled ? '0 0 10px #00d4a0' : 'none',
          }} />
          <span style={{ fontWeight: 600, color: status?.enabled ? '#00d4a0' : '#6b6b8a' }}>
            {status?.enabled ? 'SCANNER ACTIVE' : 'SCANNER OFFLINE'}
          </span>
        </div>
        <div style={{ color: '#6b6b8a', fontSize: '13px' }}>
          Last scan: <span style={{ color: '#c0c0d0' }}>{status?.last_scan_at?.slice(0, 19) ?? '—'}</span>
        </div>
        <div style={{ color: '#6b6b8a', fontSize: '13px' }}>
          Next scan: <span style={{ color: '#4a9eff' }}>{status?.enabled ? countdown || status?.next_scan_at?.slice(0, 19) : '—'}</span>
        </div>
        <div style={{ color: '#6b6b8a', fontSize: '13px' }}>
          Signals today: <span style={{ color: '#e8e8f0', fontWeight: 600 }}>{status?.signals_today ?? 0}</span>
        </div>
        <div style={{ color: '#6b6b8a', fontSize: '13px' }}>
          Open positions: <span style={{ color: '#e8e8f0', fontWeight: 600 }}>{positions.length}</span>
        </div>
      </div>

      {/* OANDA Account */}
      {oandaError ? (
        <div style={{ ...card, marginBottom: '20px', borderColor: 'rgba(255,71,87,0.3)', background: 'rgba(255,71,87,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#ff4757' }}>
            <AlertCircle size={16} />
            <span style={{ fontSize: '13px' }}><strong>OANDA not configured:</strong> {oandaError}. Add OANDA_API_KEY and OANDA_ACCOUNT_ID to your .env file.</span>
          </div>
        </div>
      ) : account && (
        <div style={{ display: 'flex', gap: '16px', marginBottom: '20px' }}>
          <AccountCard label="Account Balance" value={`$${account.balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`} sub={`${account.currency} • ${account.mode}`} />
          <AccountCard label="Net Asset Value" value={`$${account.nav.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`} />
          <AccountCard
            label="Unrealized P&L"
            value={`${account.unrealized >= 0 ? '+' : ''}$${account.unrealized.toFixed(2)}`}
            color={account.unrealized >= 0 ? '#00d4a0' : '#ff4757'}
          />
          <AccountCard label="Margin Used" value={`$${account.margin_used.toFixed(2)}`} color="#4a9eff" />
        </div>
      )}

      {/* Open positions */}
      <div style={{ ...card, marginBottom: '20px' }}>
        <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '12px' }}>
          Open Positions ({positions.length})
        </h2>
        {positions.length === 0 ? (
          <div style={{ color: '#6b6b8a', fontSize: '13px', textAlign: 'center', padding: '24px' }}>No open positions</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead>
              <tr style={{ color: '#6b6b8a', borderBottom: '1px solid #1e1e2e' }}>
                {['Symbol', 'Direction', 'Units', 'Avg Price', 'Unrealized P&L', ''].map(h => (
                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {positions.map((p, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #1a1a28', color: '#c0c0d0' }}>
                  <td style={{ padding: '8px 12px', fontWeight: 600 }}>{p.symbol}</td>
                  <td style={{ padding: '8px 12px' }}>
                    <Badge variant={p.direction === 'LONG' ? 'green' : 'red'}>{p.direction}</Badge>
                  </td>
                  <td style={{ padding: '8px 12px' }}>{p.units.toLocaleString()}</td>
                  <td style={{ padding: '8px 12px' }}>{p.avg_price.toFixed(5)}</td>
                  <td style={{ padding: '8px 12px', color: p.unrealized >= 0 ? '#00d4a0' : '#ff4757' }}>
                    {p.unrealized >= 0 ? '+' : ''}${p.unrealized.toFixed(2)}
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <Button variant="danger" size="sm" onClick={() => closePos(p.symbol)}>Close</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Signal feed */}
      <div style={card}>
        <h2 style={{ fontSize: '14px', fontWeight: 600, color: '#e8e8f0', marginBottom: '12px' }}>
          Recent Signals
        </h2>
        {signals.length === 0 ? (
          <div style={{ color: '#6b6b8a', fontSize: '13px', textAlign: 'center', padding: '24px' }}>
            No signals yet. Enable the scanner or click Manual Scan.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ color: '#6b6b8a', borderBottom: '1px solid #1e1e2e' }}>
                {['Time', 'Symbol', 'Dir', 'Entry', 'SL', 'TP', 'RR', 'Session', 'Status', 'Order ID'].map(h => (
                  <th key={h} style={{ padding: '7px 10px', textAlign: 'left', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {signals.map((s, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #1a1a28', color: '#c0c0d0' }}>
                  <td style={{ padding: '7px 10px', color: '#6b6b8a' }}>{s.fired_at?.slice(0, 16)}</td>
                  <td style={{ padding: '7px 10px', fontWeight: 600 }}>{s.symbol}</td>
                  <td style={{ padding: '7px 10px', color: s.direction === 'LONG' ? '#00d4a0' : '#ff4757' }}>{s.direction}</td>
                  <td style={{ padding: '7px 10px' }}>{s.entry_price?.toFixed(5)}</td>
                  <td style={{ padding: '7px 10px', color: '#ff4757' }}>{s.stop_loss?.toFixed(5)}</td>
                  <td style={{ padding: '7px 10px', color: '#00d4a0' }}>{s.take_profit?.toFixed(5)}</td>
                  <td style={{ padding: '7px 10px' }}>{s.risk_reward?.toFixed(2)}R</td>
                  <td style={{ padding: '7px 10px', color: '#6b6b8a' }}>{s.session}</td>
                  <td style={{ padding: '7px 10px' }}>
                    <Badge variant={statusColor(s.placement_status)}>{s.placement_status}</Badge>
                  </td>
                  <td style={{ padding: '7px 10px', color: '#4a9eff', fontFamily: 'monospace' }}>
                    {s.oanda_order_id || s.placement_error || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
