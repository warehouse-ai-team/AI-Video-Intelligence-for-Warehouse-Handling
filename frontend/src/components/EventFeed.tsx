'use client';

import { WarehouseEvent } from '@/lib/types';
import RiskBadge from './RiskBadge';

interface EventFeedProps {
  events: WarehouseEvent[];
  selectedEventId?: string;
  onSelectEvent: (event: WarehouseEvent) => void;
}

function formatBehaviour(behaviour: string) {
  return behaviour
    .split('_')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ');
}

function formatSeconds(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60)
    .toString()
    .padStart(2, '0');
  return `${m}:${s}`;
}

export default function EventFeed({ events, selectedEventId, onSelectEvent }: EventFeedProps) {
  return (
    <div className="flex h-full flex-col rounded-panel border border-border bg-surface">
      <div className="border-b border-border px-4 py-2">
        <span className="text-sm font-medium text-text-primary">Event Feed</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {events.length === 0 ? (
          <p className="p-4 text-sm text-text-muted">No events match the current filters.</p>
        ) : (
          events.map((event) => (
            <button
              key={event.event_id}
              onClick={() => onSelectEvent(event)}
              className={`flex w-full flex-col gap-1 border-b border-border px-4 py-3 text-left transition-colors hover:bg-base ${
                selectedEventId === event.event_id ? 'bg-base' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-text-primary">
                  {formatBehaviour(event.behaviour)}
                </span>
                <RiskBadge level={event.risk_level} />
              </div>
              <div className="data-readout flex items-center gap-2 text-xs text-text-muted">
                <span>{event.video_id}</span>
                <span>· {formatSeconds(event.start_time)}</span>
                <span>· score {event.risk_score}</span>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}