'use client';

import { BehaviourType, FilterState, RiskLevel } from '@/lib/types';

const RISK_LEVELS: RiskLevel[] = ['low', 'medium', 'high', 'critical'];

const BEHAVIOURS: BehaviourType[] = [
  'drop',
  'drag',
  'rough_handling',
  'unstable_stacking',
  'outside_designated_area',
  'no_equipment_used',
  'incorrect_pallet_placement',
  'push_or_throw',
  'unsafe_sequence',
  'overloading',
];

interface FiltersProps {
  bays: string[];
  filters: FilterState;
  onChange: (next: FilterState) => void;
}

function formatLabel(value: string) {
  return value
    .split('_')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ');
}

export default function Filters({ bays, filters, onChange }: FiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 border-b border-border bg-surface px-4 py-3">
      <select
        className="rounded-panel border border-border bg-base px-2 py-1 text-sm text-text-primary"
        value={filters.bay ?? ''}
        onChange={(e) => onChange({ ...filters, bay: e.target.value || undefined })}
      >
        <option value="">All bays</option>
        {bays.map((bay) => (
          <option key={bay} value={bay}>
            {bay}
          </option>
        ))}
      </select>

      <select
        className="rounded-panel border border-border bg-base px-2 py-1 text-sm text-text-primary"
        value={filters.riskLevel ?? ''}
        onChange={(e) =>
          onChange({ ...filters, riskLevel: (e.target.value || undefined) as RiskLevel | undefined })
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
        value={filters.behaviourType ?? ''}
        onChange={(e) =>
          onChange({
            ...filters,
            behaviourType: (e.target.value || undefined) as BehaviourType | undefined,
          })
        }
      >
        <option value="">All behaviours</option>
        {BEHAVIOURS.map((b) => (
          <option key={b} value={b}>
            {formatLabel(b)}
          </option>
        ))}
      </select>

      {(filters.bay || filters.riskLevel || filters.behaviourType) && (
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