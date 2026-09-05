'use client';

import { WarehouseEvent } from '@/lib/types';
import RiskBadge from './RiskBadge';

interface EventFeedProps {
  events: WarehouseEvent[];
  selectedEventId?: string;
  onSelectEvent: (event: WarehouseEvent) => void;
}

function formatBehaviour(type: string) {
  return type
    .split('_')
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(' ');
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
                  {formatBehaviour(event.behaviour_type)}
                </span>
                <RiskBadge level={event.risk_level} />
              </div>
              <div className="data-readout flex items-center gap-2 text-xs text-text-muted">
                <span>{formatTime(event.timestamp)}</span>
                {event.bay && <span>· {event.bay}</span>}
                <span>· {event.track_id}</span>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}