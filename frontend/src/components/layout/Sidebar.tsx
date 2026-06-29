'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, Brain, BookOpen, BarChart3, Zap } from 'lucide-react';

const nav = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/analysis', label: 'Analysis', icon: Brain },
  { href: '/journal', label: 'Journal', icon: BookOpen },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <div style={{
      width: '220px', minHeight: '100vh', background: '#0d0d15',
      borderRight: '1px solid #1e1e2e', display: 'flex', flexDirection: 'column', flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{ padding: '24px 20px', borderBottom: '1px solid #1e1e2e' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '32px', height: '32px', background: 'linear-gradient(135deg, #4a9eff, #00d4a0)', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Zap size={18} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#e8e8f0' }}>JARVES</div>
            <div style={{ fontSize: '10px', color: '#6b6b8a', letterSpacing: '1px' }}>TRADING SYSTEM</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '16px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link key={href} href={href} style={{ textDecoration: 'none' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                padding: '10px 12px', borderRadius: '8px', cursor: 'pointer',
                background: active ? 'rgba(74,158,255,0.12)' : 'transparent',
                color: active ? '#4a9eff' : '#6b6b8a',
                border: active ? '1px solid rgba(74,158,255,0.2)' : '1px solid transparent',
                transition: 'all 0.2s',
              }}>
                <Icon size={18} />
                <span style={{ fontSize: '14px', fontWeight: active ? 600 : 400 }}>{label}</span>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{ padding: '16px 20px', borderTop: '1px solid #1e1e2e' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#00d4a0', boxShadow: '0 0 8px #00d4a0' }} />
          <span style={{ fontSize: '12px', color: '#6b6b8a' }}>System Online</span>
        </div>
      </div>
    </div>
  );
}
