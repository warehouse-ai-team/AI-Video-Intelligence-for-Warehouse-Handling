import { RiskLevel } from '@/lib/types';

const RISK_COLOR: Record<RiskLevel, string> = {
  CRITICAL: '#E5484D',
  HIGH: '#F0883E',
  MEDIUM: '#E8C547',
  LOW: '#3FB950',
};

interface TimeRangeHighlightProps {
  behaviour: string;
  riskLevel: RiskLevel;
  startTime: number;
  endTime: number;
}

export default function TimeRangeHighlight({
  behaviour,
  riskLevel,
  startTime,
  endTime,
}: TimeRangeHighlightProps) {
  const color = RISK_COLOR[riskLevel];
  return (
    <div
      className="flex items-center justify-between rounded-panel border-l-4 bg-base px-3 py-2"
      style={{ borderColor: color }}
    >
      <span className="text-sm font-medium text-text-primary">
        {behaviour.replace(/_/g, ' ')}
      </span>
      <span className="data-readout text-xs text-text-muted">
        {startTime.toFixed(1)}s – {endTime.toFixed(1)}s
      </span>
    </div>
  );
}