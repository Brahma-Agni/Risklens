import { Badge } from '@/components/ui/badge';
import { riskPercent } from '@/lib/api';

export function RiskBadge({ value }: { value: number }) {
  const score = riskPercent(value);
  const tone =
    score >= 85
      ? 'bg-[#ff6b6b] text-black'
      : score >= 60
        ? 'bg-[#ffd93d] text-black'
        : 'bg-[#86efac] text-black';
  return (
    <Badge variant="outline" className={tone}>
      {score}
    </Badge>
  );
}
export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toUpperCase();
  const color =
    normalized.includes('BLOCK') ||
    normalized.includes('DECLINED') ||
    normalized.includes('ABUSE') ||
    normalized.includes('FRAUD') ||
    normalized.includes('CRITICAL')
      ? 'bg-[#ff6b6b]'
      : normalized.includes('REVIEW') ||
          normalized.includes('HOLD') ||
          normalized.includes('OPEN') ||
          normalized.includes('HIGH')
        ? 'bg-[#ffd93d]'
        : normalized.includes('UNAVAILABLE')
          ? 'bg-black'
          : 'bg-[#86efac]';
  return (
    <span className="inline-flex items-center gap-2 text-xs font-extrabold uppercase">
      <span className={`size-3 border-2 border-black ${color}`} />
      {status.replaceAll('_', ' ')}
    </span>
  );
}
export function DataMode({
  live,
  message,
}: {
  live: boolean;
  message?: string;
}) {
  return (
    <div
      className={`border-2 border-black px-3 py-2 text-xs font-extrabold shadow-[3px_3px_0_#000] ${live ? 'bg-[#86efac]' : 'bg-[#ffd93d]'}`}
    >
      {live
        ? 'Live backend data'
        : (message ??
          'Demo context is shown because the live dataset is empty or unavailable.')}
    </div>
  );
}
