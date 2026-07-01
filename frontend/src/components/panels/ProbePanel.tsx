import { useAppStore } from '../../store/useAppStore';
import type { UnifiedProbe } from '../../types';
import { useLocale, tModel } from '../../i18n';

export function ProbePanel() {
  const { t } = useLocale();
  const runResult = useAppStore((s) => s.runResult);
  const liveProbes = useAppStore((s) => s.liveProbes);
  const descriptor = useAppStore((s) => s.currentDescriptor);

  const probes = liveProbes.length > 0 ? liveProbes : (runResult?.probes ?? []);
  const schemaMap = new Map(descriptor?.probes.map((p) => [p.name, p]) ?? []);

  return (
    <div className="h-full min-h-0 flex flex-col">
      <div className="panel-header">{t('panel.probes')}</div>
      <div className="flex-1 overflow-y-auto p-2">
        {probes.length === 0 && !descriptor?.probes.length ? (
          <p className="text-xs text-muted p-2">{t('probe.noData')}</p>
        ) : (
          <div className="space-y-1">
            {descriptor?.probes.map((schema) => {
              const live = probes.find((p) => p.name === schema.name);
              return (
                <ProbeRow
                  key={schema.name}
                  label={tModel(descriptor.model_id, `probes.${schema.name}`, schema.label)}
                  unit={schema.unit}
                  probe={live}
                  type={schema.type}
                />
              );
            })}
            {probes
              .filter((p) => !schemaMap.has(p.name))
              .map((p) => (
                <ProbeRow
                  key={p.name}
                  label={descriptor ? tModel(descriptor.model_id, `probes.${p.name}`, p.label) : p.label}
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
