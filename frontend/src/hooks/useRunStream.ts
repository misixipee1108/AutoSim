import { useEffect, useRef } from 'react';
import { createSimApi } from '../api/client';
import { useAppStore } from '../store/useAppStore';
import type { RunStatus, UnifiedAgentDecision, UnifiedProbe, UnifiedRunResult } from '../types';

export interface UseRunStreamOptions {
  onProbe?: (probe: UnifiedProbe) => void;
  onDecision?: (decision: UnifiedAgentDecision) => void;
  onLog?: (message: string) => void;
  onStatus?: (status: RunStatus) => void;
  onComplete?: (result: UnifiedRunResult) => void;
  onError?: (error: string) => void;
}

/** Subscribe to SSE/mock stream for an existing run id. */
export function useRunStream(runId: string | null, options: UseRunStreamOptions = {}) {
  const apiMode = useAppStore((s) => s.apiMode);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  useEffect(() => {
    if (!runId) return;
    const api = createSimApi(apiMode);
    const unsubscribe = api.subscribeRun(runId, {
      onProbe: (p) => optionsRef.current.onProbe?.(p),
      onDecision: (d) => optionsRef.current.onDecision?.(d),
      onLog: (m) => optionsRef.current.onLog?.(m),
      onStatus: (s) => optionsRef.current.onStatus?.(s),
      onComplete: (r) => optionsRef.current.onComplete?.(r),
      onError: (e) => optionsRef.current.onError?.(e),
    });
    return unsubscribe;
  }, [runId, apiMode]);
}
