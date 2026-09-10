import { cn } from '@/lib/utils';

export function Card({
  title,
  subtitle,
  right,
  className,
  children,
}: {
  title?: string;
  subtitle?: string;
  right?: React.ReactNode;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={cn('rounded-xl border border-ink-line bg-ink-raised', className)}>
      {(title || right) && (
        <header className="flex items-start justify-between gap-3 border-b border-ink-line px-4 py-3">
          <div>
            {title && <h2 className="text-sm font-semibold tracking-wide text-paper">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Stat({
  label,
  value,
  tone = 'neutral',
  hint,
}: {
  label: string;
  value: React.ReactNode;
  tone?: 'neutral' | 'up' | 'down' | 'gold';
  hint?: string;
}) {
  const toneClass = {
    neutral: 'text-paper',
    up: 'text-up',
    down: 'text-down',
    gold: 'text-gold',
  }[tone];
  return (
    <div className="rounded-lg border border-ink-line bg-ink px-3 py-2.5">
      <div className="text-[11px] uppercase tracking-wider text-muted">{label}</div>
      <div className={cn('mt-1 font-mono text-lg font-semibold tabular-nums', toneClass)}>{value}</div>
      {hint && <div className="mt-0.5 text-[11px] text-muted">{hint}</div>}
    </div>
  );
}

export function Pill({
  children,
  tone = 'neutral',
}: {
  children: React.ReactNode;
  tone?: 'neutral' | 'up' | 'down' | 'gold' | 'muted';
}) {
  const toneClass = {
    neutral: 'border-ink-line bg-ink text-paper',
    up: 'border-up/30 bg-up/10 text-up',
    down: 'border-down/30 bg-down/10 text-down',
    gold: 'border-gold/30 bg-gold/10 text-gold',
    muted: 'border-ink-line bg-ink text-muted',
  }[tone];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        toneClass,
      )}
    >
      {children}
    </span>
  );
}

export function Button({
  children,
  onClick,
  variant = 'default',
  disabled,
  className,
}: {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'default' | 'primary' | 'danger';
  disabled?: boolean;
  className?: string;
}) {
  const variantClass = {
    default: 'border-ink-line bg-ink hover:border-muted text-paper',
    primary: 'border-gold/40 bg-gold/15 text-gold hover:bg-gold/25',
    danger: 'border-down/40 bg-down/10 text-down hover:bg-down/20',
  }[variant];
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors',
        'disabled:cursor-not-allowed disabled:opacity-40',
        variantClass,
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <p className="py-6 text-center text-sm text-muted">{children}</p>;
}
