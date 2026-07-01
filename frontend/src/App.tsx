import { AppShell } from './components/shell/AppShell';
import { useModels } from './hooks/useModels';
import { useLocaleStore } from './i18n';
import { useThemeStore } from './theme/themeStore';

function App() {
  useModels();
  useLocaleStore((s) => s.locale);
  useThemeStore((s) => s.theme);
  return <AppShell />;
}

export default App;
