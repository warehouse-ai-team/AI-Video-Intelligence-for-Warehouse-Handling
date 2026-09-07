'use client';

import { useMemo, useRef, useState } from 'react';
import { FilterState, WarehouseEvent } from '@/lib/types';
import { useEvents } from '@/hooks/useEvents';
import VideoPanel, { VideoPanelHandle } from './VideoPanel';
import EventFeed from './EventFeed';
import Filters from './Filters';
import IncidentReplay from './IncidentReplay';
import RiskExplanation from './RiskExplanation';
import TimeRangeHighlight from './TimeRangeHighlight';
import ChatPanel from './ChatPanel';
import ConnectionStatus from './ConnectionStatus';

const MOCK_VIDEO_DURATION_SECONDS = 120; // placeholder until real video metadata exists

export default function Dashboard() {
  const [filters, setFilters] = useState<FilterState>({});
  const { events, isLoading, error, usingMockData } = useEvents(filters);
  const [selectedEvent, setSelectedEvent] = useState<WarehouseEvent | undefined>();
  const videoRef = useRef<VideoPanelHandle>(null);

  const videoIds = useMemo(
    () => Array.from(new Set(events.map((e) => e.video_id))),
    [events]
  );

  const sameVideoEvents = useMemo(() => {
    if (!selectedEvent) return events;
    return events
      .filter((e) => e.video_id === selectedEvent.video_id)
      .sort((a, b) => a.start_time - b.start_time);
  }, [events, selectedEvent]);

  function handleSelectEvent(event: WarehouseEvent) {
    setSelectedEvent(event);
    videoRef.current?.seekTo(event.start_time);
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-border bg-surface px-4 py-3">
        <h1 className="text-base font-semibold text-text-primary">Warehouse AI Dashboard</h1>
        <div className="flex items-center gap-3">
          {usingMockData && (
            <span className="rounded-badge border border-risk-medium px-2 py-0.5 text-xs text-risk-medium">
              Backend unreachable — showing sample data
            </span>
          )}
          <ConnectionStatus />
        </div>
      </header>

      <Filters videoIds={videoIds} filters={filters} onChange={setFilters} />

      <div className="grid flex-1 grid-cols-3 gap-3 overflow-hidden p-3">
        <div className="col-span-2 flex flex-col gap-3">
          <VideoPanel
            ref={videoRef}
            activeLabel={selectedEvent ? `${selectedEvent.video_id} · ${selectedEvent.created_at}` : undefined}
            highlight={
              selectedEvent && (
                <TimeRangeHighlight
                  behaviour={selectedEvent.behaviour}
                  riskLevel={selectedEvent.risk_level}
                  startTime={selectedEvent.start_time}
                  endTime={selectedEvent.end_time}
                />
              )
            }
          />
          <IncidentReplay
            events={sameVideoEvents}
            selectedEventId={selectedEvent?.event_id}
            onSelectEvent={handleSelectEvent}
            videoDurationSeconds={MOCK_VIDEO_DURATION_SECONDS}
          />
        </div>

        <div className="col-span-1 flex min-h-0 flex-col gap-3">
          <div className="min-h-0 flex-[1.2]">
            {isLoading ? (
              <div className="flex h-full items-center justify-center rounded-panel border border-border bg-surface text-sm text-text-muted">
                Loading events…
              </div>
            ) : (
              <EventFeed
                events={events}
                selectedEventId={selectedEvent?.event_id}
                onSelectEvent={handleSelectEvent}
              />
            )}
          </div>
          <RiskExplanation event={selectedEvent} />
          <div className="min-h-0 flex-1">
            <ChatPanel events={events} selectedEvent={selectedEvent} />
          </div>
        </div>
      </div>

      {error && !usingMockData && (
        <div className="border-t border-border bg-risk-critical/10 px-4 py-2 text-xs text-risk-critical">
          {error}
        </div>
      )}
    </div>
  );
}