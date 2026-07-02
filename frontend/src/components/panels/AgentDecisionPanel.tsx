import { useAppStore } from '../../store/useAppStore';
import type { UnifiedAgentDecision } from '../../types';
import {
  useLocale,
  tRuntime,
  resolveActionRaw,
  resolveAgentReason,
  resolveParamKey,
} from '../../i18n';

const ACTION_COLORS: Record<string, string> = {
  continue: 'text-green-400',
  early_stop: 'text-yellow-400',
  adjust_params: 'text-orange-400',
  refine_mesh: 'text-purple-400',
  explain_failure: 'text-red-400',
  recommend_next: 'text-blue-400',
  mark_infeasible: 'text-red-500',
};

function formatSuggestedParams(params: Record<string, unknown>): string {
  const translated: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(params)) {
    const label = resolveParamKey(key);
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      translated[label] = value;
    } else {
      translated[label] = value;
    }
  }
  return JSON.stringify(translated, null, 2);
}

export function AgentDecisionPanel() {
  const { t } = useLocale();
  const runResult = useAppStore((s) => s.runResult);
  const liveDecisions = useAppStore((s) => s.liveDecisions);
  const decisions = liveDecisions.length > 0 ? liveDecisions : (runResult?.decisions ?? []);

  return (
    <div className="border-b border-default h-full min-h-0 flex flex-col">
      <div className="panel-header">{t('panel.agentDecisions')}</div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {decisions.length === 0 ? (
          <p className="text-xs text-muted p-2">{t('agent.noDecisions')}</p>
        ) : (
          decisions.map((d, i) => <DecisionCard key={`${d.timestamp}-${i}`} decision={d} />)
        )}
      </div>
    </div>
  );
}

function DecisionCard({ decision }: { decision: UnifiedAgentDecision }) {
  const { t } = useLocale();
  const color = ACTION_COLORS[decision.action] ?? 'text-slate-300';
  const actionLabel = tRuntime(`action.${decision.action}`, decision.action);
  const rawLabel = decision.raw_action ? resolveActionRaw(decision.raw_action) : null;

  return (
    <div className="card p-2 text-xs">
      <div className="flex justify-between items-center mb-1">
        <span className={`font-semibold uppercase ${color}`}>{actionLabel}</span>
        <span className="text-muted">{(decision.confidence * 100).toFixed(0)}%</span>
      </div>
      {decision.reason && (
        <p className="text-muted leading-relaxed">{resolveAgentReason(decision.reason)}</p>
      )}
      {decision.suggested_params && Object.keys(decision.suggested_params).length > 0 && (
        <pre className="mt-1 text-[10px] text-faint bg-panel-solid rounded p-1 overflow-auto border border-subtle">
          {formatSuggestedParams(decision.suggested_params)}
        </pre>
      )}
      {rawLabel && decision.raw_action && decision.raw_action !== decision.action && (
        <div className="text-[10px] text-faint mt-1">
          {t('agent.rawPrefix')} {rawLabel}
        </div>
      )}
    </div>
  );
}
