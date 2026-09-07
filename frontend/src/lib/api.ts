import { WarehouseEvent, RiskScore, Summary, FilterState } from './types';

const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch {
    throw new ApiError('Could not reach the backend. Is it running on port 8000?');
  }

  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = body?.detail ?? '';
    } catch {
      /* not JSON */
    }
    throw new ApiError(detail || `Request failed (${res.status})`, res.status);
  }

  return res.json() as Promise<T>;
}

// Query param names match backend/app/api/events.py exactly:
// video_id, risk_level, behaviour (not "bay", not "behaviour_type").
function buildQuery(filters: FilterState): string {
  const params = new URLSearchParams();
  if (filters.video_id) params.set('video_id', filters.video_id);
  if (filters.risk_level) params.set('risk_level', filters.risk_level);
  if (filters.behaviour) params.set('behaviour', filters.behaviour);
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

// GET /events
export function getEvents(filters: FilterState = {}): Promise<WarehouseEvent[]> {
  return request<WarehouseEvent[]>(`/events${buildQuery(filters)}`);
}

// GET /events/{event_id}
export function getEvent(eventId: string): Promise<WarehouseEvent> {
  return request<WarehouseEvent>(`/events/${eventId}`);
}

// GET /risk-scores — optional event_id filter, per her implementation
export function getRiskScores(eventId?: string): Promise<RiskScore[]> {
  const qs = eventId ? `?event_id=${eventId}` : '';
  return request<RiskScore[]>(`/risk-scores${qs}`);
}

// GET /summary — replaces the supervisor/* endpoints we'd assumed earlier.
// This one endpoint now covers "most common behaviour" and "busiest video"
// questions; there's no separate morning/afternoon endpoint, so the
// assistant will need to compute that itself from /events (Milestone D).
export function getSummary(): Promise<Summary> {
  return request<Summary>('/summary');
}

// POST /seed/sample — loads her sample pipeline events, useful for local dev/demo
export function seedSampleEvents(): Promise<{ created: number; skipped_existing: number }> {
  return request('/seed/sample', { method: 'POST' });
}

// GET /health
export function checkBackendHealth(): Promise<{ status: string }> {
  return request<{ status: string }>('/health');
}