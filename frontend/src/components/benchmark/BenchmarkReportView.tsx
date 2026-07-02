import { useMemo, useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { useLocale } from '../../i18n';
import { deriveDisplayCategory } from '../../utils/benchmarkStatus';
import { BenchmarkSummaryCards } from './BenchmarkSummaryCards';
import { BenchmarkFilterBar, type BenchmarkFilters } from './BenchmarkFilterBar';
import { BenchmarkCaseTable } from './BenchmarkCaseTable';
import { BenchmarkMarkdownPreview } from './BenchmarkMarkdownPreview';
import { BenchmarkJsonPanel } from './BenchmarkJsonPanel';

const DEFAULT_FILTERS: BenchmarkFilters = {
  categories: [],
  modelType: '',
  dopingType: '',
  failureReason: '',
};

export function BenchmarkReportView() {
  const { t } = useLocale();
  const report = useAppStore((s) => s.benchmarkReport);
  const markdown = useAppStore((s) => s.benchmarkMarkdown);
  const loading = useAppStore((s) => s.benchmarkLoading);
  const error = useAppStore((s) => s.benchmarkError);
  const [filters, setFilters] = useState<BenchmarkFilters>(DEFAULT_FILTERS);
  const [reportTab, setReportTab] = useState<'markdown' | 'json'>('markdown');

  const modelTypes = useMemo(
    () => [...new Set(report?.case_results.map((c) => c.model_type) ?? [])].sort(),
    [report],
  );
  const dopingTypes = useMemo(
    () => [...new Set(report?.case_results.map((c) => c.doping_type) ?? [])].sort(),
    [report],
  );

  const filteredCases = useMemo(() => {
    if (!report) return [];
    return report.case_results.filter((c) => {
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
  }, [report, filters]);

  if (loading && !report) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm">
        {t('benchmark.loading')}
      </div>
    );
  }

  if (error && !report) {
    return (
      <div className="flex items-center justify-center h-full error-banner text-sm m-4 rounded px-4 py-3">
        {error}
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex items-center justify-center h-full text-muted text-sm">
        {t('benchmark.selectReport')}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col min-h-0 overflow-hidden">
      <div className="panel-header shrink-0">{t('benchmark.title')}</div>
      <div className="flex-1 overflow-y-auto p-3 space-y-4 min-h-0">
        <BenchmarkSummaryCards report={report} />

        <div>
          <h3 className="text-xs font-semibold text-muted mb-2 uppercase">
            {t('benchmark.caseResults')}
            <span className="ml-2 text-faint font-normal">
              ({filteredCases.length}/{report.case_results.length})
            </span>
          </h3>
          <BenchmarkFilterBar
            filters={filters}
            modelTypes={modelTypes}
            dopingTypes={dopingTypes}
            onChange={setFilters}
          />
          <div className="mt-2">
            <BenchmarkCaseTable cases={report.case_results} filters={filters} />
          </div>
        </div>

        <div>
          <div className="tab-bar flex shrink-0 mb-2">
            <button
              type="button"
              className={`tab-btn ${reportTab === 'markdown' ? 'tab-btn-active' : ''}`}
              onClick={() => setReportTab('markdown')}
            >
              {t('benchmark.tabMarkdown')}
            </button>
            <button
              type="button"
              className={`tab-btn ${reportTab === 'json' ? 'tab-btn-active' : ''}`}
              onClick={() => setReportTab('json')}
            >
              {t('benchmark.tabJson')}
            </button>
          </div>
          {reportTab === 'markdown' && markdown ? (
            <BenchmarkMarkdownPreview markdown={markdown} />
          ) : (
            <BenchmarkJsonPanel report={report} filteredCases={filteredCases} />
          )}
        </div>
      </div>
    </div>
  );
}
