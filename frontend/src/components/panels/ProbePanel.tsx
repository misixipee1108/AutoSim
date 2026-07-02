import { useAppStore } from '../../store/useAppStore';
import type { UnifiedProbe } from '../../types';
import {
  useLocale,
  inferModelIdFromProject,
  resolveProbeLabel,
} from '../../i18n';

export function ProbePanel() {
  const { t } = useLocale();
  const runResult = useAppStore((s) => s.runResult);
  const liveProbes = useAppStore((s) => s.liveProbes);
  const currentProject = useAppStore((s) => s.currentProject);
  const modelId = inferModelIdFromProject(currentProject);

  const probes = liveProbes.length > 0 ? liveProbes : (runResult?.probes ?? []);

  return (
    <div className="h-full min-h-0 flex flex-col">
      <div className="panel-header">{t('panel.probes')}</div>
      <div className="flex-1 overflow-y-auto p-2">
        {probes.length === 0 ? (
          <p className="text-xs text-muted p-2">{t('probe.noData')}</p>
        ) : (
          <div className="space-y-1">
            {probes.map((p) => (
              <ProbeRow
                key={p.name}
                label={resolveProbeLabel(modelId, p.name, p.label)}
                unit={p.unit}
                probe={p}
                type={p.type}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ProbeRow({
  label,
  unit,
  probe,
  type,
}: {
  label: string;
  unit?: string;
  probe?: UnifiedProbe;
  type: string;
}) {
  const { t } = useLocale();
  let display = t('probe.empty');
  if (probe?.value !== undefined && probe.value !== null) {
    if (type === 'boolean') {
      display = probe.value ? t('probe.true') : t('probe.false');
    } else if (typeof probe.value === 'number') {
      display = Math.abs(probe.value) >= 1e4 || (Math.abs(probe.value) < 1e-3 && probe.value !== 0)
        ? probe.value.toExponential(3)
        : probe.value.toPrecision(4);
      if (unit) display += ` ${unit}`;
    } else {
      display = String(probe.value);
    }
  }

  return (
    <div className="flex justify-between items-center text-xs py-0.5 border-b border-subtle">
      <span className="text-muted">{label}</span>
      <span className={`font-mono ${probe ? 'text-primary' : 'text-faint'}`}>{display}</span>
    </div>
  );
}
