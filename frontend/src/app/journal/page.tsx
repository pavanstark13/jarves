import { TradeTable } from '@/components/journal/TradeTable';
import { Card } from '@/components/ui/Card';

export default function JournalPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Trade Journal</h1>
          <p className="text-text-muted text-sm mt-0.5">Every trade logged, every pattern visible</p>
        </div>
      </div>
      <Card className="p-5">
        <TradeTable />
      </Card>
    </div>
  );
}
