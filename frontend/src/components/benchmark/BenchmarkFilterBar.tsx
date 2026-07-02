import type { DisplayCategory } from '../../types';
import { useLocale, resolveEnum } from '../../i18n';

export interface BenchmarkFilters {
  categories: DisplayCategory[];
  modelType: string;
  dopingType: string;
  failureReason: string;
}

interface Props {
  filters: BenchmarkFilters;
  modelTypes: string[];
  dopingTypes: string[];
  onChange: (filters: BenchmarkFilters) => void;
}

const ALL_CATEGORIES: DisplayCategory[] = [
  'passed',
  'warning',
  'failed',
  'numerical_only',
  'validation_unavailable',
];

export function BenchmarkFilterBar({ filters, modelTypes, dopingTypes, onChange }: Props) {
  const { t, tRuntime } = useLocale();

  const toggleCategory = (cat: DisplayCategory) => {
    const next = filters.categories.includes(cat)
      ? filters.categories.filter((c) => c !== cat)
      : [...filters.categories, cat];
    onChange({ ...filters, categories: next });
  };

  return (
    <div className="flex flex-wrap items-end gap-3 p-2 border border-default rounded bg-panel-solid text-xs">
      <div className="flex flex-col gap-1">
        <span className="text-faint">{t('benchmark.filterCategory')}</span>
        <div className="flex flex-wrap gap-1">
          {ALL_CATEGORIES.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => toggleCategory(cat)}
              className={`px-2 py-0.5 rounded border text-[10px] ${
                filters.categories.length === 0 || filters.categories.includes(cat)
                  ? 'segment-btn-active border-accent'
                  : 'border-subtle text-muted'
              }`}
            >
              {tRuntime(`benchmarkCategory.${cat}`, cat)}
            </button>
          ))}
        </div>
      </div>

      <label className="flex flex-col gap-1">
        <span className="text-faint">{t('benchmark.filterModelType')}</span>
        <select
          value={filters.modelType}
          onChange={(e) => onChange({ ...filters, modelType: e.target.value })}
          className="min-w-[120px]"
        >
          <option value="">{t('benchmark.filterAll')}</option>
          {modelTypes.map((m) => (
            <option key={m} value={m}>{resolveEnum('modelType', m)}</option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-faint">{t('benchmark.filterDopingType')}</span>
        <select
          value={filters.dopingType}
          onChange={(e) => onChange({ ...filters, dopingType: e.target.value })}
          className="min-w-[120px]"
        >
          <option value="">{t('benchmark.filterAll')}</option>
          {dopingTypes.map((d) => (
            <option key={d} value={d}>{resolveEnum('dopingType', d)}</option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 flex-1 min-w-[160px]">
        <span className="text-faint">{t('benchmark.filterFailureReason')}</span>
        <input
          type="text"
          value={filters.failureReason}
          onChange={(e) => onChange({ ...filters, failureReason: e.target.value })}
          placeholder={t('benchmark.filterFailurePlaceholder')}
        />
      </label>
    </div>
  );
}
