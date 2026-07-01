import { useAppStore } from '../../store/useAppStore';
import type { ParameterSchema } from '../../types';
import { useLocale, tModel, tModelOptionHelp } from '../../i18n';
import { QuantityInput } from './QuantityInput';
import { SelectWithHelp } from './SelectWithHelp';
import { DelayedTooltip } from '../ui/DelayedTooltip';

function getConfigValue(config: Record<string, unknown>, name: string): unknown {
  const parts = name.split('.');
  let cur: unknown = config;
  for (const p of parts) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = (cur as Record<string, unknown>)[p];
  }
  return cur;
}

function ParamField({ param, modelId }: { param: ParameterSchema; modelId: string }) {
  const config = useAppStore((s) => s.config);
  const setConfigValue = useAppStore((s) => s.setConfigValue);
  const value = getConfigValue(config, param.name);

  const label = tModel(modelId, `params.${param.name}.label`, param.label);
  const description = tModel(modelId, `params.${param.name}.description`, param.description ?? '');

  if (param.type === 'select') {
    const options = (param.options ?? []).map((o) => ({
      value: o.value,
      label: tModel(modelId, `params.${param.name}.options.${o.value}`, o.label),
      help: tModelOptionHelp(
        modelId,
        param.name,
        o.value,
        param.description ?? o.label,
      ),
    }));

    return (
      <label className="flex flex-col gap-1">
        <span className="text-[11px] text-muted">{label}</span>
        <SelectWithHelp
          value={String(value ?? param.default ?? '')}
          onChange={(v) => setConfigValue(param.name, v)}
          options={options}
        />
      </label>
    );
  }

  if (param.type === 'boolean') {
    return (
      <DelayedTooltip content={description}>
        <label className="flex items-center gap-2 text-xs text-primary cursor-help">
          <input
            type="checkbox"
            checked={Boolean(value ?? param.default)}
            onChange={(e) => setConfigValue(param.name, e.target.checked)}
          />
          {label}
        </label>
      </DelayedTooltip>
    );
  }

  if (param.unit) {
    return (
      <QuantityInput
        param={param}
        label={label}
        description={description}
      />
    );
  }

  const inputType = param.type === 'integer' ? 'number' : 'number';
  const step = param.step ?? (param.type === 'integer' ? 1 : 'any');

  return (
    <label className="flex flex-col gap-1">
      <DelayedTooltip content={description}>
        <span className="text-[11px] text-muted cursor-help">{label}</span>
      </DelayedTooltip>
      <input
        type={inputType}
        step={step}
        min={param.min}
        max={param.max}
        value={Number(value ?? param.default ?? 0)}
        onChange={(e) => {
          const v = param.type === 'integer' ? parseInt(e.target.value, 10) : parseFloat(e.target.value);
          setConfigValue(param.name, v);
        }}
      />
    </label>
  );
}

export function DynamicParameterForm() {
  const { t } = useLocale();
  const descriptor = useAppStore((s) => s.currentDescriptor);
  const selectedNode = useAppStore((s) => s.selectedTreeNode);

  if (!descriptor) return null;

  const node = descriptor.tree_nodes.find((n) => n.id === selectedNode);
  const groups = node?.parameter_groups ?? [];
  const params = descriptor.parameters.filter((p) => groups.includes(p.group ?? 'General'));
  const sectionTitle = node
    ? tModel(descriptor.model_id, `tree.${node.id}`, node.label)
    : t('form.parameters');

  return (
    <div className="p-3 space-y-3">
      <div className="text-xs font-semibold text-primary">{sectionTitle}</div>
      {params.length === 0 ? (
        <p className="text-xs text-muted">{t('form.noParameters')}</p>
      ) : (
        params.map((p) => <ParamField key={p.name} param={p} modelId={descriptor.model_id} />)
      )}
    </div>
  );
}
