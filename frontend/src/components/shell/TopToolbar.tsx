import { useAppStore } from '../../store/useAppStore';
import { useRun } from '../../hooks/useModels';
import { useLocale, tRuntime, tModel } from '../../i18n';
import { useThemeStore } from '../../theme/themeStore';
import { SelectWithHelp } from '../model/SelectWithHelp';

const STATUS_CLASS: Record<string, string> = {
  pending: 'status-pending',
  running: 'status-running',
  completed: 'status-completed',
  completed_with_warning: 'status-warning',
  failed: 'status-failed',
  early_stopped: 'status-early_stopped',
};

export function TopToolbar() {
  const { t, locale, setLocale } = useLocale();
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const models = useAppStore((s) => s.models);
  const currentModelId = useAppStore((s) => s.currentModelId);
  const selectModel = useAppStore((s) => s.selectModel);
  const config = useAppStore((s) => s.config);
  const setConfig = useAppStore((s) => s.setConfig);
  const runResult = useAppStore((s) => s.runResult);
  const agentBackend = useAppStore((s) => s.agentBackend);
  const setAgentBackend = useAppStore((s) => s.setAgentBackend);
  const apiMode = useAppStore((s) => s.apiMode);
  const setApiMode = useAppStore((s) => s.setApiMode);
  const { isRunning, runStatus, startRun, stopRun } = useRun();

  const parseConfigText = (text: string, name: string): Record<string, unknown> | null => {
    try {
      if (name.endsWith('.yaml') || name.endsWith('.yml')) {
        const lines = text.split(/\r?\n/);
        const flat: Record<string, unknown> = {};
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith('#')) continue;
          const idx = trimmed.indexOf(':');
          if (idx <= 0) continue;
          const key = trimmed.slice(0, idx).trim();
          let val: unknown = trimmed.slice(idx + 1).trim();
          if (val === 'true') val = true;
          else if (val === 'false') val = false;
          else if (typeof val === 'string' && !Number.isNaN(Number(val))) val = Number(val);
          flat[key] = val;
        }
        return flat;
      }
      return JSON.parse(text) as Record<string, unknown>;
    } catch {
      return null;
    }
  };

  const importConfig = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,.yaml,.yml';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      const parsed = parseConfigText(await file.text(), file.name);
      if (!parsed) {
        window.alert(t('shell.importFailed'));
        return;
      }
      setConfig({ ...config, ...parsed });
    };
    input.click();
  };

  const exportConfig = () => {
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentModelId ?? 'config'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportResult = () => {
    if (!runResult) return;
    const blob = new Blob([JSON.stringify(runResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `result_${runResult.run_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <header className="flex items-center gap-3 px-4 py-2 border-b border-default bg-toolbar shrink-0">
      <span className="text-sm font-bold text-accent tracking-wide">AutoSim</span>
      <span className="divider">|</span>

      <label className="flex items-center gap-2 text-xs text-muted">
        {t('shell.model')}
        <select
          value={currentModelId ?? ''}
          onChange={(e) => selectModel(e.target.value)}
          disabled={isRunning}
          className="min-w-[180px]"
        >
          {models.map((m) => (
            <option key={m.model_id} value={m.model_id}>
              {tModel(m.model_id, 'name', m.model_name)}
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

      <button type="button" className="btn-secondary text-xs" disabled={isRunning} onClick={importConfig}>
        {t('shell.import')}
      </button>
      <button type="button" className="btn-secondary text-xs" disabled={isRunning} onClick={exportConfig}>
        {t('shell.exportConfig')}
      </button>
      <button type="button" className="btn-secondary text-xs" disabled={!runResult} onClick={exportResult}>
        {t('shell.exportResult')}
      </button>

      {runStatus && (
        <span className={`status-badge ${STATUS_CLASS[runStatus] ?? 'status-pending'}`}>
          {tRuntime(`status.${runStatus}`, runStatus)}
        </span>
      )}

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

      {!isRunning ? (
        <button type="button" className="btn-primary" onClick={startRun}>
          {t('shell.run')}
        </button>
      ) : (
        <button type="button" className="btn-secondary" onClick={stopRun}>
          {t('shell.stop')}
        </button>
      )}
    </header>
  );
}
