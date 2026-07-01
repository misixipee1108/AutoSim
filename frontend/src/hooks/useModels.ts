import { useEffect } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useAppStore } from '../store/useAppStore';

export function useModels() {
  const loadModels = useAppStore((s) => s.loadModels);
  const models = useAppStore((s) => s.models);

  useEffect(() => {
    loadModels();
  }, [loadModels]);

  return models;
}

export function useCurrentModel() {
  return useAppStore(
    useShallow((s) => ({
      descriptor: s.currentDescriptor,
      modelId: s.currentModelId,
      config: s.config,
      selectModel: s.selectModel,
      setConfigValue: s.setConfigValue,
    })),
  );
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
