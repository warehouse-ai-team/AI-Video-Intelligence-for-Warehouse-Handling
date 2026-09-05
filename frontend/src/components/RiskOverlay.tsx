import { RiskLevel, BoundingBox } from '@/lib/types';

const OVERLAY_COLOR: Record<RiskLevel, string> = {
  critical: '#E5484D',
  high: '#F0883E',
  medium: '#E8C547',
  low: '#3FB950',
};

interface RiskOverlayProps {
  bbox: BoundingBox;
  riskLevel: RiskLevel;
  label: string;
}

// Positioned as a percentage of the video's natural frame; bbox values
// are expected in the same coordinate space the CV pipeline exports.
export default function RiskOverlay({ bbox, riskLevel, label }: RiskOverlayProps) {
  const color = OVERLAY_COLOR[riskLevel];

  return (
    <div
      className="pointer-events-none absolute border-2"
      style={{
        left: `${bbox.x}px`,
        top: `${bbox.y}px`,
        width: `${bbox.width}px`,
        height: `${bbox.height}px`,
        borderColor: color,
      }}
    >
      <span
        className="data-readout absolute -top-6 left-0 rounded-badge px-1.5 py-0.5 text-xs font-medium text-base"
        style={{ backgroundColor: color }}
      >
        {label}
      </span>
    </div>
  );
}