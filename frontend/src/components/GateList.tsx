import { Gate } from '@/types';

/**
 * The gate list is the whole point of the console: every rule the agent
 * checked, with the measurement that produced the verdict.
 */
export function GateList({ gates, title }: { gates: Gate[]; title?: string }) {
  if (!gates.length) {
    return <p className="text-sm text-muted">No evaluation yet.</p>;
  }
  return (
    <div className="space-y-1.5">
      {title && <p className="text-[11px] uppercase tracking-wider text-muted">{title}</p>}
      {gates.map((gate) => (
        <div
          key={gate.name}
          className="flex items-start gap-2.5 rounded-lg border border-ink-line bg-ink px-3 py-2"
        >
          <span
            className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
              gate.passed ? 'bg-up' : 'bg-down'
            }`}
            aria-hidden
          />
          <div className="min-w-0">
            <div className="font-mono text-xs uppercase tracking-wide text-paper">{gate.name}</div>
            <div className="text-xs leading-relaxed text-muted">{gate.detail}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
