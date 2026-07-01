import { useThemeStore } from '../theme/themeStore';

export function useChartTheme() {
  const theme = useThemeStore((s) => s.theme);

  return {
    theme,
    axisColor: theme === 'dark' ? '#94a3b8' : '#64748b',
    axisNameColor: theme === 'dark' ? '#64748b' : '#94a3b8',
    splitLineColor: theme === 'dark' ? '#1e293b' : '#e2e8f0',
    legendColor: theme === 'dark' ? '#94a3b8' : '#475569',
    titleColor: theme === 'dark' ? '#94a3b8' : '#475569',
    axisLineColor: theme === 'dark' ? '#334155' : '#cbd5e1',
    backgroundColor: 'transparent',
  };
}
