import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number, decimals = 5): string {
  return price.toFixed(decimals);
}

export function formatPct(value: number, decimals = 2): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatPnl(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}$${Math.abs(value).toFixed(2)}`;
}

export function formatR(value: number): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}R`;
}

export function signalColor(signal: string): string {
  if (['BULLISH', 'DETECTED', 'ACTIVE'].includes(signal)) return 'text-bull';
  if (['BEARISH'].includes(signal)) return 'text-bear';
  return 'text-text-muted';
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 0.75) return '#00d4a0';
  if (confidence >= 0.5) return '#4a9eff';
  return '#ff4757';
}
