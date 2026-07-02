import type { BenchmarkCaseReport, BenchmarkReport } from '../../types';

interface Props {
  report: BenchmarkReport;
  filteredCases?: BenchmarkCaseReport[];
}

export function BenchmarkJsonPanel({ report, filteredCases }: Props) {
  const payload = filteredCases
    ? { ...report, case_results: filteredCases }
    : report;

  return (
    <div className="overflow-y-auto max-h-96 border border-default rounded bg-panel-solid">
      <pre className="p-3 text-[10px] font-mono text-primary whitespace-pre-wrap break-words">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </div>
  );
}
