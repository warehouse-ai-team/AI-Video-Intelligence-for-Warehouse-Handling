import { RiskLevel } from '@/lib/types';

const RISK_STYLES: Record<RiskLevel, { label: string; dot: string; text: string }> = {
  CRITICAL: { label: 'Critical', dot: 'bg-risk-critical', text: 'text-risk-critical' },
  HIGH: { label: 'High', dot: 'bg-risk-high', text: 'text-risk-high' },
  MEDIUM: { label: 'Medium', dot: 'bg-risk-medium', text: 'text-risk-medium' },
  LOW: { label: 'Low', dot: 'bg-risk-low', text: 'text-risk-low' },
};

export default function RiskBadge({ level }: { level: RiskLevel }) {
  const style = RISK_STYLES[level];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-badge border border-border bg-base px-2 py-0.5 text-xs font-medium ${style.text}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {style.label}
    </span>
  );
}