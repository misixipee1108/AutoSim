import { create } from 'zustand';

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'autosim_theme';

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: 'dark',
  setTheme: (theme) => {
    localStorage.setItem(STORAGE_KEY, theme);
    document.documentElement.dataset.theme = theme;
    set({ theme });
  },
}));

export function initTheme(): void {
  const stored = localStorage.getItem(STORAGE_KEY) as Theme | null;
  const theme: Theme = stored === 'light' ? 'light' : 'dark';
  document.documentElement.dataset.theme = theme;
  useThemeStore.setState({ theme });
}
