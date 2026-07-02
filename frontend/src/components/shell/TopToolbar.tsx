import { useAppStore } from '../../store/useAppStore';
import { useRun } from '../../hooks/useModels';
import { useLocale, resolveTemplateTitle } from '../../i18n';
import { useThemeStore } from '../../theme/themeStore';
import { SelectWithHelp } from '../model/SelectWithHelp';
import type { SimulationProject } from '../../types';

const STATUS_CLASS: Record<string, string> = {
  pending: 'status-pending',
  running: 'status-running',
  completed: 'status-completed',
  completed_with_warning: 'status-warning',
  failed: 'status-failed',
  early_stopped: 'status-early_stopped',
};

export function TopToolbar() {
  const { t, tRuntime, locale, setLocale } = useLocale();
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const projectTemplates = useAppStore((s) => s.projectTemplates);
  const currentTemplateId = useAppStore((s) => s.currentTemplateId);
  const loadProjectTemplate = useAppStore((s) => s.loadProjectTemplate);
  const importProject = useAppStore((s) => s.importProject);
  const currentProject = useAppStore((s) => s.currentProject);
  const runResult = useAppStore((s) => s.runResult);
  const agentBackend = useAppStore((s) => s.agentBackend);
  const setAgentBackend = useAppStore((s) => s.setAgentBackend);
  const apiMode = useAppStore((s) => s.apiMode);
  const setApiMode = useAppStore((s) => s.setApiMode);
  const workspace = useAppStore((s) => s.workspace);
  const setWorkspace = useAppStore((s) => s.setWorkspace);
  const { isRunning, runStatus, startRun, stopRun } = useRun();
  const isBenchmark = workspace === 'benchmark';

  const downloadBlob = (content: string, filename: string, mime: string) => {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importProjectFile = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const parsed = JSON.parse(await file.text()) as SimulationProject;
        if (parsed.schema_version !== '2.0') {
          window.alert(t('shell.importFailed'));
          return;
        }
        importProject(parsed);
      } catch {
        window.alert(t('shell.importFailed'));
      }
    };
    input.click();
  };

  const exportProject = () => {
    if (!currentProject) return;
    downloadBlob(
      JSON.stringify(currentProject, null, 2),
      `${currentProject.project_id}.json`,
      'application/json',
    );
  };

  const exportResult = () => {
    if (!runResult) return;
    downloadBlob(
      JSON.stringify(runResult, null, 2),
      `result_${runResult.run_id}.json`,
      'application/json',
    );
  };

  return (
    <header className="flex items-center gap-3 px-4 py-2 border-b border-default bg-toolbar shrink-0">
      <span className="text-sm font-bold text-accent tracking-wide">AutoSim</span>
      <span className="divider">|</span>

      <div className="segment-group">
        <button
          type="button"
          disabled={isRunning}
          onClick={() => setWorkspace('simulation')}
          className={`segment-btn ${workspace === 'simulation' ? 'segment-btn-active' : ''}`}
        >
          {t('shell.workspaceSimulation')}
        </button>
        <button
          type="button"
          disabled={isRunning}
          onClick={() => setWorkspace('benchmark')}
          className={`segment-btn ${workspace === 'benchmark' ? 'segment-btn-active' : ''}`}
        >
          {t('shell.workspaceBenchmark')}
        </button>
      </div>

      <span className="divider">|</span>

      {!isBenchmark && (
      <>
      <label className="flex items-center gap-2 text-xs text-muted">
        {t('shell.projectTemplate')}
        <select
          value={currentTemplateId}
          onChange={(e) => loadProjectTemplate(e.target.value)}
          disabled={isRunning}
          className="min-w-[180px]"
        >
          {projectTemplates.map((tpl) => (
            <option key={tpl.template_id} value={tpl.template_id}>
              {resolveTemplateTitle(tpl.template_id, tpl.title)}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-xs text-muted">
        {t('shell.agent')}
        <SelectWithHelp
          value={agentBackend}
          onChange={setAgentBackend}
          disabled={isRunning}
          options={[
            { value: 'rules', label: t('agentBackend.rules'), help: t('agentBackend.optionsHelp.rules') },
            { value: 'deepseek', label: t('agentBackend.deepseek'), help: t('agentBackend.optionsHelp.deepseek') },
            { value: 'hybrid', label: t('agentBackend.hybrid'), help: t('agentBackend.optionsHelp.hybrid') },
          ]}
        />
      </label>

      <div className="flex-1" />

      <button type="button" className="btn-secondary text-xs" disabled={isRunning} onClick={importProjectFile}>
        {t('shell.import')}
      </button>
      <button type="button" className="btn-secondary text-xs" disabled={isRunning || !currentProject} onClick={exportProject}>
        {t('shell.exportProject')}
      </button>
      <button type="button" className="btn-secondary text-xs" disabled={!runResult} onClick={exportResult}>
        {t('shell.exportResult')}
      </button>

      {runStatus && (
        <span className={`status-badge ${STATUS_CLASS[runStatus] ?? 'status-pending'}`}>
          {tRuntime(`status.${runStatus}`, runStatus)}
        </span>
      )}
      </>
      )}

      {isBenchmark && <div className="flex-1" />}

      <div className="segment-group">
        <button
          type="button"
          disabled={isRunning}
          onClick={() => setTheme('light')}
          className={`segment-btn ${theme === 'light' ? 'segment-btn-active' : ''}`}
        >
          {t('shell.themeLight')}
        </button>
        <button
          type="button"
          disabled={isRunning}
          onClick={() => setTheme('dark')}
          className={`segment-btn ${theme === 'dark' ? 'segment-btn-active' : ''}`}
        >
          {t('shell.themeDark')}
        </button>
      </div>

      <div className="segment-group">
        <button
          type="button"
          disabled={isRunning}
          onClick={() => setLocale('en')}
          className={`segment-btn ${locale === 'en' ? 'segment-btn-active' : ''}`}
        >
          {t('shell.langEn')}
        </button>
        <button
          type="button"
          disabled={isRunning}
          onClick={() => setLocale('zh')}
          className={`segment-btn ${locale === 'zh' ? 'segment-btn-active' : ''}`}
        >
          {t('shell.langZh')}
        </button>
      </div>

      <label className="flex items-center gap-1 text-xs text-faint">
        <input
          type="checkbox"
          checked={apiMode === 'live'}
          onChange={(e) => setApiMode(e.target.checked ? 'live' : 'mock')}
          disabled={isRunning}
        />
        {t('shell.liveApi')}
      </label>

      {!isBenchmark && (
        !isRunning ? (
          <button type="button" className="btn-primary" onClick={startRun}>
            {t('shell.run')}
          </button>
        ) : (
          <button type="button" className="btn-secondary" onClick={stopRun}>
            {t('shell.stop')}
          </button>
        )
      )}
    </header>
  );
}
