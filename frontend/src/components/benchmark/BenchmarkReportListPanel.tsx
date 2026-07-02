import { useAppStore } from '../../store/useAppStore';
import { useLocale } from '../../i18n';
import { shortGitCommit, shortRunId } from '../../utils/benchmarkStatus';

export function BenchmarkReportListPanel() {
  const { t } = useLocale();
  const reports = useAppStore((s) => s.benchmarkReports);
  const selected = useAppStore((s) => s.selectedBenchmarkRunId);
  const loading = useAppStore((s) => s.benchmarkLoading);
  const selectReport = useAppStore((s) => s.selectBenchmarkReport);
  const loadReports = useAppStore((s) => s.loadBenchmarkReports);
  const runSuite = useAppStore((s) => s.runBenchmarkSuite);
  const running = useAppStore((s) => s.benchmarkRunning);

  return (
    <div className="h-full flex flex-col">
      <div className="panel-header flex items-center justify-between gap-2">
        <span>{t('benchmark.reportList')}</span>
        <div className="flex gap-1">
          <button
            type="button"
            className="btn-ghost text-[10px] px-1"
            onClick={() => runSuite()}
            disabled={loading || running}
          >
            {running ? t('benchmark.running') : t('benchmark.runSuite')}
          </button>
          <button
            type="button"
            className="btn-ghost text-[10px] px-1"
            onClick={() => loadReports()}
            disabled={loading || running}
          >
            {t('benchmark.refresh')}
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto py-1">
        {reports.length === 0 ? (
          <p className="text-xs text-muted px-3 py-2">{t('benchmark.noReports')}</p>
        ) : (
          <ul>
            {reports.map((r) => (
              <li key={r.run_id}>
                <button
                  type="button"
                  onClick={() => selectReport(r.run_id)}
                  className={`w-full text-left px-3 py-2 text-xs transition-colors tree-item ${
                    selected === r.run_id ? 'tree-item-active' : ''
                  }`}
                >
                  <div className="font-mono text-primary">{shortRunId(r.run_id)}</div>
                  <div className="text-[10px] text-faint mt-0.5">{r.timestamp}</div>
                  <div className="flex gap-2 mt-1 text-[10px]">
                    <span className="text-green-400">{r.passed_count}P</span>
                    <span className="text-yellow-400">{r.warning_count}W</span>
                    <span className="text-red-400">{r.failed_count}F</span>
                  </div>
                  {r.git_commit && (
                    <div className="text-[10px] text-faint font-mono mt-0.5">
                      {shortGitCommit(r.git_commit)}
                    </div>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
