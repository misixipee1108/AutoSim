import type { BenchmarkCaseReport, DisplayCategory } from '../types';

import { tMetric } from '../i18n/translations';



/** Client-side fallback when display_category is missing from API. */

export function deriveDisplayCategory(caseRow: BenchmarkCaseReport): DisplayCategory {

  if (caseRow.display_category) return caseRow.display_category;

  if (caseRow.outcome === 'fail') return 'failed';

  if (caseRow.validation_mode === 'numerical_only') return 'numerical_only';

  if (caseRow.validation_mode === 'validation_unavailable') return 'validation_unavailable';

  if (caseRow.outcome === 'warning') return 'warning';

  return 'passed';

}



export const CATEGORY_BADGE_CLASS: Record<DisplayCategory, string> = {

  passed: 'benchmark-category-passed',

  warning: 'benchmark-category-warning',

  failed: 'benchmark-category-failed',

  numerical_only: 'benchmark-category-neutral',

  validation_unavailable: 'benchmark-category-neutral',

};



export function formatMetricValue(v: number | boolean | null | undefined): string {

  if (v === null || v === undefined) return '—';

  if (typeof v === 'boolean') return String(v);

  if (Math.abs(v) >= 1e4 || (Math.abs(v) < 1e-3 && v !== 0)) return v.toExponential(3);

  return v.toPrecision(4);

}



export function formatMetricsSummary(

  metrics: Record<string, number | boolean | null | undefined>,

  max = 3,

): string {

  const entries = Object.entries(metrics).slice(0, max);

  if (entries.length === 0) return '—';

  return entries.map(([k, v]) => `${tMetric(k, k)}=${formatMetricValue(v)}`).join(', ');

}



export function formatErrorsTolerances(

  errors: Record<string, number | null | undefined>,

  tolerances: Record<string, number>,

): string {

  const keys = Object.keys(errors);

  if (keys.length === 0) return '—';

  return keys

    .slice(0, 3)

    .map((k) => {

      const err = errors[k];

      const tol = tolerances[k];

      const errStr = err == null ? '—' : `${(err * 100).toFixed(1)}%`;

      const tolStr = tol == null ? '—' : `${(tol * 100).toFixed(1)}%`;

      return `${tMetric(k, k)}: ${errStr}/${tolStr}`;

    })

    .join('; ');

}



export function shortGitCommit(commit: string | null | undefined): string {

  if (!commit) return '—';

  return commit.slice(0, 7);

}



export function shortRunId(runId: string): string {

  return runId.length > 12 ? runId.slice(0, 12) + '…' : runId;

}


