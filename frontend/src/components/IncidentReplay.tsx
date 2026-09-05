'use client';

import { WarehouseEvent } from '@/lib/types';
import RiskBadge from './RiskBadge';

const RISK_DOT: Record<string, string> = {
  critical: 'bg-risk-critical',
  high: 'bg-risk-high',
  medium: 'bg-risk-medium',
  low: 'bg-risk-low',
};

interface IncidentReplayProps {
  events: WarehouseEvent[]; // events for the currently loaded video, in time order
  selectedEventId?: string;
  onSelectEvent: (event: WarehouseEvent) => void;
  videoDurationSeconds: number;
}

export default function IncidentReplay({
  events,
  selectedEventId,
  onSelectEvent,
  videoDurationSeconds,
}: IncidentReplayProps) {
  return (
    <div className="rounded-panel border border-border bg-surface p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-text-primary">Incident Replay</span>
        <span className="text-xs text-text-muted">{events.length} incidents this video</span>
      </div>

      <div className="relative h-8 rounded-badge bg-base">
        {events.map((event) => {
          const positionPct = videoDurationSeconds
            ? (event.video_time_seconds / videoDurationSeconds) * 100
            : 0;
          const isSelected = event.event_id === selectedEventId;

          return (
            <button
              key={event.event_id}
              title={`${event.behaviour_type} at ${event.video_time_seconds}s`}
              onClick={() => onSelectEvent(event)}
              className={`absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-surface transition-transform hover:scale-125 ${
                RISK_DOT[event.risk_level]
              } ${isSelected ? 'scale-125' : ''}`}
              style={{ left: `${positionPct}%` }}
            />
          );
        })}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {events.map((event) => (
          <button
            key={event.event_id}
            onClick={() => onSelectEvent(event)}
            className={`flex items-center gap-2 rounded-panel border border-border px-2 py-1 text-xs transition-colors hover:border-accent ${
              event.event_id === selectedEventId ? 'border-accent' : ''
            }`}
          >
            <span className="data-readout text-text-muted">{event.video_time_seconds}s</span>
            <RiskBadge level={event.risk_level} />
          </button>
        ))}
      </div>
    </div>
  );
}