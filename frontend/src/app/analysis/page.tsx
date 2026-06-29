import { AnalysisPanel } from '@/components/analysis/AnalysisPanel';

export default function AnalysisPage() {
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">AI Analysis</h1>
        <p className="text-text-muted text-sm mt-0.5">
          Evidence-based setup evaluation — not price prediction
        </p>
      </div>
      <AnalysisPanel />
    </div>
  );
}
