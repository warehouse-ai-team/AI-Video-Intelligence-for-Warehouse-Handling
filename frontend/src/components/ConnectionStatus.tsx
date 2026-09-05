'use client';

import { useEffect, useState } from 'react';
import { checkBackendHealth } from '@/lib/api';

type Status = 'checking' | 'online' | 'offline';

export default function ConnectionStatus() {
  const [status, setStatus] = useState<Status>('checking');

  useEffect(() => {
    let cancelled = false;
    checkBackendHealth()
      .then(() => !cancelled && setStatus('online'))
      .catch(() => !cancelled && setStatus('offline'));
    return () => {
      cancelled = true;
    };
  }, []);

  const dotColor =
    status === 'online' ? 'bg-risk-low' : status === 'offline' ? 'bg-risk-critical' : 'bg-risk-medium';

  return (
    <div className="flex items-center gap-1.5 text-xs text-text-muted">
      <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
      Backend {status}
    </div>
  );
}