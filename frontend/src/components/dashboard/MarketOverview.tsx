'use client';
import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { TrendingUp, TrendingDown, Minus, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'US30'];
const NAMES: Record<string, string> = {
  XAUUSD: 'Gold', EURUSD: 'Euro / Dollar', GBPUSD: 'Cable', US30: 'Dow Jones',
};

interface Quote {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
}

export function MarketOverview() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const results = await Promise.all(
          SYMBOLS.map(async (sym) => {
            const res = await fetch(`/api/market-data/${sym}/quote`);
            if (!res.ok) throw new Error(await res.text());
            return res.json() as Promise<Quote>;
          })
        );
        setQuotes(results);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load quotes');
      } finally {
        setLoading(false);
      }
    }
    load();
    const id = setInterval(load, 60_000); // refresh every 60s
    return () => clearInterval(id);
  }, []);

  if (loading) return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
      {SYMBOLS.map(s => (
        <Card key={s} className="p-4 flex items-center justify-center h-24">
          <Loader2 className="w-5 h-5 animate-spin text-text-muted" />
        </Card>
      ))}
    </div>
  );

  if (error) return (
    <Card className="p-4 border-bear/30">
      <p className="text-bear text-sm">Market data unavailable: {error}</p>
      <p className="text-text-muted text-xs mt-1">Check your TWELVE_DATA_API_KEY in the backend .env</p>
    </Card>
  );

  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
      {quotes.map((q) => {
        const bull = q.change_pct >= 0;
        const Icon = bull ? TrendingUp : TrendingDown;
        return (
          <Card key={q.symbol} className="p-4 hover:border-info/30 transition-colors cursor-pointer">
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="text-xs text-text-muted">{NAMES[q.symbol] ?? q.symbol}</p>
                <p className="font-bold text-text-primary">{q.symbol}</p>
              </div>
            </div>
            <p className="text-xl font-mono font-semibold text-text-primary">
              {q.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 5 })}
            </p>
            <div className={cn('flex items-center gap-1 mt-1 text-sm font-medium', bull ? 'text-bull' : 'text-bear')}>
              <Icon className="w-3.5 h-3.5" />
              {bull ? '+' : ''}{q.change_pct.toFixed(2)}%
            </div>
          </Card>
        );
      })}
    </div>
  );
}
