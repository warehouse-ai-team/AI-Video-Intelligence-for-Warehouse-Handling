'use client';

import { Behaviour, FilterState, RiskLevel } from '@/lib/types';

const RISK_LEVELS: RiskLevel[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];

const BEHAVIOURS: Behaviour[] = [
  'dropping',
  'throwing',
  'dragging',
  'rough_handling',
  'improper_stacking',
  'unstable_stacking',
  'outside_designated_area',
  'strap_assisted_handling',
  'stepping_on_carton',
  'unsafe_loading_sequence',
];

interface FiltersProps {
  videoIds: string[];
  filters: FilterState;
  onChange: (next: FilterState) => void;
}

function formatLabel(value: string) {
  return value
    .split('_')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ');
}

export default function Filters({ videoIds, filters, onChange }: FiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-border bg-surface px-4 py-3">
      {/* No "bay" concept in the real schema — filtering by video_id instead */}
      <select
        className="rounded-panel border border-border bg-base px-2 py-1 text-sm text-text-primary"
        value={filters.video_id ?? ''}
        onChange={(e) => onChange({ ...filters, video_id: e.target.value || undefined })}
      >
        <option value="">All videos</option>
        {videoIds.map((id) => (
          <option key={id} value={id}>
            {id}
          </option>
        ))}
      </select>

      <select
        className="rounded-panel border border-border bg-base px-2 py-1 text-sm text-text-primary"
        value={filters.risk_level ?? ''}
        onChange={(e) =>
          onChange({ ...filters, risk_level: (e.target.value || undefined) as RiskLevel | undefined })
        }
      >
        <option value="">All risk levels</option>
        {RISK_LEVELS.map((level) => (
          <option key={level} value={level}>
            {formatLabel(level)}
          </option>
        ))}
      </select>

      <select
        className="rounded-panel border border-border bg-base px-2 py-1 text-sm text-text-primary"
        value={filters.behaviour ?? ''}
        onChange={(e) =>
          onChange({ ...filters, behaviour: (e.target.value || undefined) as Behaviour | undefined })
        }
      >
        <option value="">All behaviours</option>
        {BEHAVIOURS.map((b) => (
          <option key={b} value={b}>
            {formatLabel(b)}
          </option>
        ))}
      </select>

      {(filters.video_id || filters.risk_level || filters.behaviour) && (
        <button
          onClick={() => onChange({})}
          className="text-sm text-text-muted hover:text-text-primary"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}