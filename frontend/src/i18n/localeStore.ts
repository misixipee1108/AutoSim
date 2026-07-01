import { create } from 'zustand';
import type { Locale } from './types';

const STORAGE_KEY = 'autosim_locale';

interface LocaleState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

export const useLocaleStore = create<LocaleState>((set) => ({
  locale: 'en',
  setLocale: (locale) => {
    localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
    document.title = locale === 'zh' ? 'AutoSim 仿真工作台' : 'AutoSim';
    set({ locale });
  },
}));

export function initLocale(): void {
  const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
  const locale: Locale = stored === 'zh' ? 'zh' : 'en';
  document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en';
  document.title = locale === 'zh' ? 'AutoSim 仿真工作台' : 'AutoSim';
  useLocaleStore.setState({ locale });
}
