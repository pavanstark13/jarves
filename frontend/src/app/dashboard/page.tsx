import { DirectionalBias } from '@/components/dashboard/DirectionalBias';
import { SessionWinRates } from '@/components/dashboard/SessionWinRates';
import { MarketHours } from '@/components/dashboard/MarketHours';
import { StyleRadar } from '@/components/dashboard/StyleRadar';
import { AnalyticsMatrix } from '@/components/dashboard/AnalyticsMatrix';
import { SystemParameters } from '@/components/dashboard/SystemParameters';
import { TradingCalendar } from '@/components/dashboard/TradingCalendar';
import { ProfitTarget } from '@/components/dashboard/ProfitTarget';

const label: React.CSSProperties = {
  fontSize: '10px',
  letterSpacing: '1.5px',
  textTransform: 'uppercase',
  color: '#7070a0',
  fontWeight: 500,
};

export default function DashboardPage() {
  return (
    <div style={{ background: '#07071a', minHeight: '100vh', padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Top header bar */}
      <div style={{
        background: '#0d0d22',
        border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: '12px',
        padding: '14px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '16px', fontWeight: 700, color: '#f0f0ff', letterSpacing: '0.5px' }}>
              FTM-1017638 ★
            </span>
            <span style={{
              fontSize: '10px', fontWeight: 700, padding: '2px 8px', borderRadius: '4px',
              background: 'rgba(0,229,204,0.15)', color: '#00e5cc', letterSpacing: '1px',
            }}>AUTH</span>
            <span style={{
              fontSize: '10px', fontWeight: 700, padding: '2px 8px', borderRadius: '4px',
              background: 'rgba(0,229,160,0.12)', color: '#00e5a0', letterSpacing: '1px',
            }}>SHARE ACTIVE</span>
          </div>
          <span style={{ ...label, fontSize: '9px' }}>
            $25K · 2-Step Plus · P2 · E-Trader · $25,000.00 · CTrade · SINCE Jun 24, 2024
          </span>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '20px', fontWeight: 800, color: '#00d4a0', fontFamily: 'monospace' }}>
            +$1,267.35
          </div>
          <div style={{ ...label, fontSize: '9px', color: '#00d4a0' }}>+5.07% ROI</div>
        </div>
      </div>

      {/* Directional Bias — full width */}
      <DirectionalBias />

      {/* 3-column: Session Win Rates | Market Hours | Style Radar */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>
        <SessionWinRates />
        <MarketHours />
        <StyleRadar />
      </div>

      {/* Analytics Matrix — full width */}
      <AnalyticsMatrix />

      {/* 2-column: System Parameters (wider) | Trading Calendar */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: '16px' }}>
        <SystemParameters />
        <TradingCalendar />
      </div>

      {/* Profit Target — full width */}
      <ProfitTarget />

    </div>
  );
}
