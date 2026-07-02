import { Fragment, useMemo, useState } from 'react';
import type { BenchmarkCaseReport } from '../../types';
import { useLocale, tRuntime, resolveEnum } from '../../i18n';
import {
  CATEGORY_BADGE_CLASS,
  deriveDisplayCategory,
  formatErrorsTolerances,
  formatMetricsSummary,
} from '../../utils/benchmarkStatus';
import type { BenchmarkFilters } from './BenchmarkFilterBar';

type SortKey =
  | 'case_id'
  | 'model_type'
  | 'doping_type'
  | 'display_category'
  | 'runtime_s';

interface Props {
  cases: BenchmarkCaseReport[];
  filters: BenchmarkFilters;
}

export function BenchmarkCaseTable({ cases, filters }: Props) {
  const { t } = useLocale();
  const [sortKey, setSortKey] = useState<SortKey>('case_id');
  const [sortAsc, setSortAsc] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return cases.filter((c) => {
      const cat = deriveDisplayCategory(c);
      if (filters.categories.length > 0 && !filters.categories.includes(cat)) return false;
      if (filters.modelType && c.model_type !== filters.modelType) return false;
      if (filters.dopingType && c.doping_type !== filters.dopingType) return false;
      if (
        filters.failureReason &&
        !(c.failure_reason ?? '').toLowerCase().includes(filters.failureReason.toLowerCase())
      ) {
        return false;
      }
      return true;
    });
  }, [cases, filters]);

  const sorted = useMemo(() => {
    const copy = [...filtered];
    copy.sort((a, b) => {
      let av: string | number = '';
      let bv: string | number = '';
      if (sortKey === 'display_category') {
        av = deriveDisplayCategory(a);
        bv = deriveDisplayCategory(b);
      } else {
        av = a[sortKey] as string | number;
        bv = b[sortKey] as string | number;
      }
      if (av < bv) return sortAsc ? -1 : 1;
      if (av > bv) return sortAsc ? 1 : -1;
      return 0;
    });
    return copy;
  }, [filtered, sortKey, sortAsc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const sortIndicator = (key: SortKey) => (sortKey === key ? (sortAsc ? ' ↑' : ' ↓') : '');

  if (sorted.length === 0) {
    return <p className="text-xs text-muted py-4 text-center">{t('benchmark.noCasesMatch')}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs min-w-[900px]">
        <thead>
          <tr className="text-faint border-b border-default">
            <SortTh label={t('benchmark.colCaseId')} onClick={() => toggleSort('case_id')} suffix={sortIndicator('case_id')} />
            <SortTh label={t('benchmark.colModelType')} onClick={() => toggleSort('model_type')} suffix={sortIndicator('model_type')} />
            <SortTh label={t('benchmark.colDopingType')} onClick={() => toggleSort('doping_type')} suffix={sortIndicator('doping_type')} />
            <SortTh label={t('benchmark.colCategory')} onClick={() => toggleSort('display_category')} suffix={sortIndicator('display_category')} />
            <th className="text-left py-1 px-1">{t('benchmark.colSolverStatus')}</th>
            <th className="text-left py-1 px-1">{t('benchmark.colValidationStatus')}</th>
            <th className="text-left py-1 px-1">{t('benchmark.colRunStatus')}</th>
            <th className="text-left py-1 px-1">{t('benchmark.colKeyMetrics')}</th>
            <th className="text-left py-1 px-1">{t('benchmark.colRelError')}</th>
            <th className="text-left py-1 px-1">{t('benchmark.colWarnings')}</th>
            <th className="text-left py-1 px-1">{t('benchmark.colFailureReason')}</th>
            <SortTh label={t('benchmark.colRuntime')} onClick={() => toggleSort('runtime_s')} suffix={sortIndicator('runtime_s')} />
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => {
            const cat = deriveDisplayCategory(c);
            const isOpen = expanded === c.case_id;
            return (
              <Fragment key={c.case_id}>
                <tr
                  className="border-b border-subtle hover:bg-hover cursor-pointer"
                  onClick={() => setExpanded(isOpen ? null : c.case_id)}
                >
                  <td className="py-1 px-1 font-mono text-primary">{c.case_id}</td>
                  <td className="py-1 px-1">{resolveEnum('modelType', c.model_type)}</td>
                  <td className="py-1 px-1">{resolveEnum('dopingType', c.doping_type)}</td>
                  <td className="py-1 px-1">
                    <span className={`status-badge ${CATEGORY_BADGE_CLASS[cat]}`}>
                      {tRuntime(`benchmarkCategory.${cat}`, cat)}
                    </span>
                  </td>
                  <td className="py-1 px-1">{tRuntime(`solverStatus.${c.solver_status}`, c.solver_status)}</td>
                  <td className="py-1 px-1">
                    {c.validation_status_display
                      ? tRuntime(`validationStatus.${c.validation_status_display}`, c.validation_status_display)
                      : t('solver.empty')}
                  </td>
                  <td className="py-1 px-1">{tRuntime(`runStatus.${c.run_status}`, c.run_status)}</td>
                  <td className="py-1 px-1 font-mono text-[10px] max-w-[140px] truncate" title={formatMetricsSummary(c.key_metrics, 10)}>
                    {formatMetricsSummary(c.key_metrics)}
                  </td>
                  <td className="py-1 px-1 font-mono text-[10px] max-w-[120px] truncate">
                    {formatErrorsTolerances(c.relative_errors, c.tolerances)}
                  </td>
                  <td className="py-1 px-1 text-[10px] text-muted max-w-[120px] truncate" title={c.warnings.join('; ')}>
                    {c.warnings.length > 0 ? c.warnings[0] : t('solver.empty')}
                  </td>
                  <td className="py-1 px-1 text-[10px] text-red-300 max-w-[140px] truncate" title={c.failure_reason ?? ''}>
                    {c.failure_reason ?? t('solver.empty')}
                  </td>
                  <td className="py-1 px-1 font-mono text-right">{c.runtime_s.toFixed(2)}</td>
                </tr>
                {isOpen && (
                  <tr className="border-b border-subtle bg-panel-solid">
                    <td colSpan={12} className="p-2">
                      <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                        <div>
                          <div className="text-faint mb-1">{t('benchmark.colKeyMetrics')}</div>
                          <pre className="overflow-auto max-h-32 p-1 border border-subtle rounded">
                            {JSON.stringify(c.key_metrics, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <div className="text-faint mb-1">{t('benchmark.referenceMetrics')}</div>
                          <pre className="overflow-auto max-h-32 p-1 border border-subtle rounded">
                            {JSON.stringify(c.reference_metrics, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <div className="text-faint mb-1">{t('benchmark.checks')}</div>
                          <pre className="overflow-auto max-h-32 p-1 border border-subtle rounded">
                            {JSON.stringify(c.checks, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <div className="text-faint mb-1">{t('benchmark.colWarnings')}</div>
                          <pre className="overflow-auto max-h-32 p-1 border border-subtle rounded">
                            {c.warnings.length > 0 ? c.warnings.join('\n') : t('solver.empty')}
                          </pre>
                        </div>
                      </div>
                      {c.description && (
                        <p className="text-[10px] text-muted mt-2">{c.description}</p>
                      )}
                      <p className="text-[10px] text-faint mt-1">
                        {t('benchmark.validationMode')}: {tRuntime(`validationMode.${c.validation_mode}`, c.validation_mode)}
                        {' · '}
                        {t('benchmark.outcome')}: {tRuntime(`outcome.${c.outcome}`, c.outcome)}
                      </p>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SortTh({
  label,
  onClick,
  suffix,
}: {
  label: string;
  onClick: () => void;
  suffix: string;
}) {
  return (
    <th className="text-left py-1 px-1">
      <button type="button" className="text-faint hover:text-primary" onClick={onClick}>
        {label}{suffix}
      </button>
    </th>
  );
}
