import { useAppStore } from '../../store/useAppStore';
import type { ParameterSchema } from '../../types';
import {
  useLocale,
  inferModelIdFromProject,
  resolveParamDescription,
  resolveParamLabel,
  resolveParamOption,
  resolveParamOptionHelp,
  resolveTreeLabel,
} from '../../i18n';
import { SelectWithHelp } from './SelectWithHelp';
import { DelayedTooltip } from '../ui/DelayedTooltip';
import { getProjectValue } from '../../utils/projectParameters';
import type { ModelTreeNode } from '../../types/project';

function findTreeNode(roots: ModelTreeNode[], nodeId: string): ModelTreeNode | null {
  for (const root of roots) {
    if (root.id === nodeId) return root;
    if (root.children?.length) {
      const found = findTreeNode(root.children, nodeId);
      if (found) return found;
    }
  }
  return null;
}

function ProjectParamField({ param }: { param: ParameterSchema }) {
  const project = useAppStore((s) => s.currentProject)!;
  const setProjectValue = useAppStore((s) => s.setProjectValue);
  const value = getProjectValue(project, param.name);
  const modelId = inferModelIdFromProject(project);
  const label = resolveParamLabel(modelId, param);
  const description = resolveParamDescription(modelId, param);

  if (param.type === 'select') {
    const options = (param.options ?? []).map((o) => ({
      value: o.value,
      label: resolveParamOption(modelId, param, o.value, o.label),
      help: resolveParamOptionHelp(modelId, param, o.value, o.label),
    }));
    return (
      <label className="flex flex-col gap-1">
        <DelayedTooltip content={description}>
          <span className="text-[11px] text-muted cursor-help">{label}</span>
        </DelayedTooltip>
        <SelectWithHelp
          value={String(value ?? param.default ?? '')}
          onChange={(v) => setProjectValue(param.name, v)}
          options={options}
        />
      </label>
    );
  }

  if (param.type === 'boolean') {
    return (
      <label className="flex items-center gap-2 text-xs text-primary">
        <input
          type="checkbox"
          checked={Boolean(value ?? param.default)}
          onChange={(e) => setProjectValue(param.name, e.target.checked)}
        />
        <DelayedTooltip content={description}>
          <span className="cursor-help">{label}</span>
        </DelayedTooltip>
      </label>
    );
  }

  if (param.unit) {
    return (
      <ProjectQuantityField
        param={param}
        label={label}
        description={description}
        value={value}
        onChange={(v) => setProjectValue(param.name, v)}
      />
    );
  }

  return (
    <label className="flex flex-col gap-1">
      <DelayedTooltip content={description}>
        <span className="text-[11px] text-muted cursor-help">{label}</span>
      </DelayedTooltip>
      <input
        type="number"
        step={param.type === 'integer' ? 1 : 'any'}
        min={param.min}
        max={param.max}
        value={Number(value ?? param.default ?? 0)}
        onChange={(e) => {
          const v = param.type === 'integer' ? parseInt(e.target.value, 10) : parseFloat(e.target.value);
          setProjectValue(param.name, v);
        }}
      />
    </label>
  );
}

function ProjectQuantityField({
  param,
  label,
  description,
  value,
  onChange,
}: {
  param: ParameterSchema;
  label: string;
  description: string;
  value: unknown;
  onChange: (v: number) => void;
}) {
  const num = typeof value === 'number' ? value : Number(param.default ?? 0);
  return (
    <label className="flex flex-col gap-1">
      <DelayedTooltip content={description}>
        <span className="text-[11px] text-muted cursor-help">{label}</span>
      </DelayedTooltip>
      <input
        type="text"
        value={`${num}[${param.unit}]`}
        onChange={(e) => {
          const m = e.target.value.match(/^([-+eE0-9.]+)/);
          if (m) onChange(parseFloat(m[1]));
        }}
      />
    </label>
  );
}

export function DynamicParameterForm() {
  const { t } = useLocale();
  const projectParameters = useAppStore((s) => s.projectParameters);
  const selectedTreePath = useAppStore((s) => s.selectedTreePath);
  const projectTreeSchema = useAppStore((s) => s.projectTreeSchema);

  const selectedNode = selectedTreePath
    ? findTreeNode(projectTreeSchema?.roots ?? [], selectedTreePath)
    : null;

  const sectionTitle = selectedTreePath
    ? resolveTreeLabel(selectedTreePath, selectedNode?.label ?? selectedTreePath.split('.').pop() ?? '', {
        studyType: selectedNode?.study_type,
        interfaceId: selectedNode?.interface_id,
        physicsCategory: selectedNode?.physics_category,
        parameterGroup: selectedNode?.parameter_group,
      })
    : t('form.parameters');

  return (
    <div className="p-3 space-y-3">
      <div className="text-xs font-semibold text-primary">{sectionTitle}</div>
      {projectParameters.length === 0 ? (
        <p className="text-xs text-muted">{t('form.noParameters')}</p>
      ) : (
        projectParameters.map((p) => <ProjectParamField key={p.name} param={p} />)
      )}
    </div>
  );
}
