import { WarehouseEvent } from '@/lib/types';
import RiskBadge from './RiskBadge';

function formatBehaviour(type: string) {
  return type
    .split('_')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ');
}

export default function RiskExplanation({ event }: { event?: WarehouseEvent }) {
  if (!event) {
    return (
      <div className="rounded-panel border border-border bg-surface p-4">
        <p className="text-sm text-text-muted">Select an event to see its risk explanation.</p>
      </div>
    );
  }

  return (
    <div className="rounded-panel border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-medium text-text-primary">
          {formatBehaviour(event.behaviour_type)}
        </h2>
        <RiskBadge level={event.risk_level} />
      </div>

      <dl className="data-readout grid grid-cols-2 gap-y-1 text-xs text-text-muted">
        <dt>Track ID</dt>
        <dd className="text-text-primary">{event.track_id}</dd>
        <dt>Confidence</dt>
        <dd className="text-text-primary">{Math.round(event.confidence * 100)}%</dd>
        <dt>Bay</dt>
        <dd className="text-text-primary">{event.bay ?? '—'}</dd>
        <dt>Timestamp</dt>
        <dd className="text-text-primary">{new Date(event.timestamp).toLocaleString()}</dd>
      </dl>

      {event.risk_explanation && (
        <p className="mt-3 text-sm text-text-primary">{event.risk_explanation}</p>
      )}

      {/* Responsible-AI framing: observed behaviour vs confirmed damage are never conflated. */}
      <p className="mt-3 border-t border-border pt-2 text-xs text-text-muted">
        This reflects a detected behaviour and its risk classification, not confirmed physical
        damage. High-risk events should be reviewed by a supervisor before action is taken.
      </p>
    </div>
  );
}