import { WarehouseEvent, RiskScore, FilterState } from './types';

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
    throw new ApiError('Could not reach the backend. Is it running?');
  }

  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = body?.detail ?? '';
    } catch {
      /* response wasn't JSON */
    }
    throw new ApiError(detail || `Request failed (${res.status})`, res.status);
  }

  return res.json() as Promise<T>;
}

function buildQuery(filters: FilterState): string {
  const params = new URLSearchParams();
  if (filters.bay) params.set('bay', filters.bay);
  if (filters.riskLevel) params.set('risk_level', filters.riskLevel);
  if (filters.behaviourType) params.set('behaviour_type', filters.behaviourType);
  if (filters.dateRange?.from) params.set('from', filters.dateRange.from);
  if (filters.dateRange?.to) params.set('to', filters.dateRange.to);
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

// GET /events — matches Day 2/4 backend plan: filterable by bay/date/risk-level.
export function getEvents(filters: FilterState = {}): Promise<WarehouseEvent[]> {
  return request<WarehouseEvent[]>(`/events${buildQuery(filters)}`);
}

// GET /events/{id}
export function getEvent(eventId: string): Promise<WarehouseEvent> {
  return request<WarehouseEvent>(`/events/${eventId}`);
}

// POST /events — used by CV/Behaviour pipeline normally, exposed here for
// completeness / manual testing from the frontend during integration.
export function createEvent(event: Omit<WarehouseEvent, 'event_id'>): Promise<WarehouseEvent> {
  return request<WarehouseEvent>('/events', {
    method: 'POST',
    body: JSON.stringify(event),
  });
}

// GET /risk-scores
export function getRiskScores(eventId?: string): Promise<RiskScore[]> {
  const qs = eventId ? `?event_id=${eventId}` : '';
  return request<RiskScore[]>(`/risk-scores${qs}`);
}

// --- Supervisor-style aggregate queries (Day 5 backend plan) ---
// These back the AI assistant so it calls real endpoints instead of
// guessing from free text. Backend route names are assumptions until
// Member 3 confirms the exact paths — update the paths below to match.

export interface BaySummary {
  bay: string;
  incident_count: number;
  highest_risk_level: string;
}

export function getBusiestBay(): Promise<BaySummary> {
  return request<BaySummary>('/supervisor/busiest-bay');
}

export interface BehaviourSummary {
  behaviour_type: string;
  count: number;
}

export function getMostCommonBehaviour(): Promise<BehaviourSummary> {
  return request<BehaviourSummary>('/supervisor/most-common-behaviour');
}

export interface TimeComparison {
  morning_count: number;
  afternoon_count: number;
}

export function compareMorningAfternoon(date?: string): Promise<TimeComparison> {
  const qs = date ? `?date=${date}` : '';
  return request<TimeComparison>(`/supervisor/morning-vs-afternoon${qs}`);
}

// GET /health — used once on app load to show a connection-status indicator
// rather than silently failing everywhere if the backend isn't up.
export function checkBackendHealth(): Promise<{ status: string }> {
  return request<{ status: string }>('/health');
}