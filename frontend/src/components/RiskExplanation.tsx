import { WarehouseEvent } from '@/lib/types';
import RiskBadge from './RiskBadge';

function formatBehaviour(behaviour: string) {
  return behaviour
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
        <h2 className="text-sm font-medium text-text-primary">{formatBehaviour(event.behaviour)}</h2>
        <RiskBadge level={event.risk_level} />
      </div>

      <dl className="data-readout grid grid-cols-2 gap-y-1 text-xs text-text-muted">
        <dt>Video</dt>
        <dd className="text-text-primary">{event.video_id}</dd>
        <dt>Confidence</dt>
        <dd className="text-text-primary">{Math.round(event.confidence * 100)}%</dd>
        <dt>Risk score</dt>
        <dd className="text-text-primary">{event.risk_score}/100</dd>
        <dt>Duration</dt>
        <dd className="text-text-primary">{(event.end_time - event.start_time).toFixed(1)}s</dd>
      </dl>

      {/* reason is Behaviour Intelligence's own explanation; risk_explanation is the risk engine's scoring narrative */}
      <p className="mt-3 text-sm text-text-primary">{event.reason}</p>
      <p className="mt-2 text-sm text-text-muted">{event.risk_explanation}</p>

      <p className="mt-3 border-t border-border pt-2 text-xs text-text-muted">
        Status: <span className="text-text-primary">Potential damage risk</span> — this reflects a
        detected behaviour and its risk classification, not confirmed physical damage. High or
        critical events should be reviewed by a supervisor before action is taken.
      </p>
    </div>
  );
}