import { useEffect } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useAppStore } from '../store/useAppStore';

export function useModels() {
  const loadProjectTemplates = useAppStore((s) => s.loadProjectTemplates);
  const loadProjectTemplate = useAppStore((s) => s.loadProjectTemplate);

  useEffect(() => {
    void Promise.allSettled([
      loadProjectTemplates(),
      loadProjectTemplate('pn_stationary'),
    ]);
  }, [loadProjectTemplates, loadProjectTemplate]);
}

export function useRun() {
  return useAppStore(
    useShallow((s) => ({
      runId: s.runId,
      runStatus: s.runStatus,
      runResult: s.runResult,
      isRunning: s.isRunning,
      startRun: s.startRun,
      stopRun: s.stopRun,
      logs: s.logs,
      liveProbes: s.liveProbes,
      liveDecisions: s.liveDecisions,
    })),
  );
}
