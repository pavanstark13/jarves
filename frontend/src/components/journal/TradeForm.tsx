'use client';
import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { X } from 'lucide-react';
import type { Trade, TradeFormData } from '@/types/trade';

interface Props {
  onSubmit: (trade: Trade) => void;
  onCancel: () => void;
}

export function TradeForm({ onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<TradeFormData>({
    symbol: 'XAUUSD', direction: 'LONG', entry_price: 0,
    stop_loss: 0, take_profit: 0, position_size: 0.1,
    session: 'LONDON', notes: '',
  });

  const inputStyle = {
    background: '#0a0a0f', border: '1px solid #1e1e2e', color: '#e8e8f0',
    borderRadius: '6px', padding: '8px 12px', fontSize: '13px', width: '100%',
  };
  const labelStyle = { fontSize: '12px', color: '#6b6b8a', display: 'block', marginBottom: '4px' };

  const set = (k: keyof TradeFormData, v: string | number) =>
    setForm(prev => ({ ...prev, [k]: v }));

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trade: Trade = {
      ...form, id: Date.now().toString(),
      status: 'OPEN', entry_time: new Date().toISOString(),
    };
    onSubmit(trade);
  }

  return (
    <Card style={{ width: '480px', maxHeight: '90vh', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#e8e8f0' }}>Add Trade</h2>
        <button onClick={onCancel} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6b6b8a' }}><X size={20} /></button>
      </div>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div>
            <label style={labelStyle}>Symbol</label>
            <select value={form.symbol} onChange={e => set('symbol', e.target.value)} style={inputStyle}>
              {['XAUUSD', 'EURUSD', 'GBPUSD', 'US30'].map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label style={labelStyle}>Direction</label>
            <select value={form.direction} onChange={e => set('direction', e.target.value as 'LONG' | 'SHORT')} style={inputStyle}>
              <option value="LONG">LONG</option>
              <option value="SHORT">SHORT</option>
            </select>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
          {[
            { k: 'entry_price', label: 'Entry Price' },
            { k: 'stop_loss', label: 'Stop Loss' },
            { k: 'take_profit', label: 'Take Profit' },
          ].map(({ k, label }) => (
            <div key={k}>
              <label style={labelStyle}>{label}</label>
              <input type="number" step="0.00001" value={form[k as keyof TradeFormData] as number}
                onChange={e => set(k as keyof TradeFormData, parseFloat(e.target.value))}
                style={inputStyle} />
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div>
            <label style={labelStyle}>Position Size (lots)</label>
            <input type="number" step="0.01" value={form.position_size}
              onChange={e => set('position_size', parseFloat(e.target.value))} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Session</label>
            <select value={form.session} onChange={e => set('session', e.target.value as Trade['session'])} style={inputStyle}>
              {['LONDON', 'NEW_YORK', 'ASIA', 'OVERLAP'].map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label style={labelStyle}>Notes</label>
          <textarea value={form.notes} onChange={e => set('notes', e.target.value)}
            rows={3} style={{ ...inputStyle, resize: 'vertical' as const }} />
        </div>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', marginTop: '4px' }}>
          <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
          <Button type="submit" variant="primary">Add Trade</Button>
        </div>
      </form>
    </Card>
  );
}
