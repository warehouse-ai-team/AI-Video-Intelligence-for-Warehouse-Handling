'use client';

import { useEffect, useState, useCallback } from 'react';
import { WarehouseEvent, FilterState } from '@/lib/types';
import { getEvents, ApiError } from '@/lib/api';
import { mockEvents } from '@/lib/mockData';

interface UseEventsResult {
  events: WarehouseEvent[];
  isLoading: boolean;
  error: string | null;
  usingMockData: boolean;
  refetch: () => void;
}

export function useEvents(filters: FilterState): UseEventsResult {
  const [events, setEvents] = useState<WarehouseEvent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [usingMockData, setUsingMockData] = useState(false);

  const fetchEvents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getEvents(filters);
      setEvents(data);
      setUsingMockData(false);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Unexpected error loading events';
      setError(message);
      setEvents(mockEvents);
      setUsingMockData(true);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  return { events, isLoading, error, usingMockData, refetch: fetchEvents };
}