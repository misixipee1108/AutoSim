import type { BenchmarkReport } from '../../types';
import { useLocale } from '../../i18n';
import { shortGitCommit } from '../../utils/benchmarkStatus';

interface Props {
  report: BenchmarkReport;
}

export function BenchmarkSummaryCards({ report }: Props) {
  const { t } = useLocale();
  const { summary, environment } = report;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <Card label={t('benchmark.totalCases')} value={String(summary.total)} />
        <Card label={t('benchmark.passed')} value={String(summary.passed_count)} accent="passed" />
        <Card label={t('benchmark.warnings')} value={String(summary.warning_count)} accent="warning" />
        <Card label={t('benchmark.failed')} value={String(summary.failed_count)} accent="failed" />
        <Card label={t('benchmark.totalRuntime')} value={`${summary.total_runtime_s.toFixed(2)} s`} mono />
        <Card
          label={t('benchmark.overall')}
          value={summary.overall_passed ? t('benchmark.overallPass') : t('benchmark.overallFail')}
          accent={summary.overall_passed ? 'passed' : 'failed'}
        />
        <Card
          label={t('benchmark.gitCommit')}
          value={shortGitCommit(report.git_commit)}
          title={report.git_commit ?? undefined}
          mono
        />
        <Card label={t('benchmark.timestamp')} value={report.timestamp} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
        <Card label={t('benchmark.suite')} value={report.benchmark_suite} />
        <Card label={t('benchmark.version')} value={report.autosim_version} mono />
        <Card label={t('benchmark.python')} value={environment.python_version} mono />
        <Card label={t('benchmark.platform')} value={environment.platform} wide />
        <Card label={t('benchmark.hostname')} value={environment.hostname ?? t('solver.empty')} mono />
        <Card label={t('benchmark.outputDir')} value={report.output_dir} wide mono />
      </div>
    </div>
  );
}

function Card({
  label,
  value,
  mono,
  wide,
  accent,
  title,
}: {
  label: string;
  value: string;
  mono?: boolean;
  wide?: boolean;
  accent?: 'passed' | 'warning' | 'failed';
  title?: string;
}) {
  const accentClass =
    accent === 'passed'
      ? 'text-green-400'
      : accent === 'warning'
        ? 'text-yellow-400'
        : accent === 'failed'
          ? 'text-red-400'
          : 'text-primary';

  return (
    <div className={`card px-3 py-2 ${wide ? 'md:col-span-2' : ''}`} title={title}>
      <div className="text-[10px] text-faint uppercase">{label}</div>
      <div className={`text-sm truncate ${mono ? 'font-mono text-xs' : ''} ${accentClass}`}>{value}</div>
    </div>
  );
}
