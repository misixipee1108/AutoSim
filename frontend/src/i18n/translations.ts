import { useLocaleStore } from './localeStore';
import type { Locale } from './types';

import enUi from './locales/en/ui.json';
import enRuntime from './locales/en/runtime.json';
import enPn from './locales/en/models/pn_junction_1d.json';
import enFb from './locales/en/models/falling_block.json';
import zhUi from './locales/zh/ui.json';
import zhRuntime from './locales/zh/runtime.json';
import zhPn from './locales/zh/models/pn_junction_1d.json';
import zhFb from './locales/zh/models/falling_block.json';

function flattenUi(obj: Record<string, unknown>, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (typeof v === 'string') out[key] = v;
    else if (v && typeof v === 'object') Object.assign(out, flattenUi(v as Record<string, unknown>, key));
  }
  return out;
}

const UI: Record<Locale, Record<string, string>> = {
  en: flattenUi(enUi as Record<string, unknown>),
  zh: flattenUi(zhUi as Record<string, unknown>),
};

const RUNTIME: Record<Locale, Record<string, string>> = {
  en: flattenUi(enRuntime as Record<string, unknown>),
  zh: flattenUi(zhRuntime as Record<string, unknown>),
};

const MODELS: Record<Locale, Record<string, Record<string, unknown>>> = {
  en: {
    pn_junction_1d: enPn as Record<string, unknown>,
    falling_block: enFb as Record<string, unknown>,
  },
  zh: {
    pn_junction_1d: zhPn as Record<string, unknown>,
    falling_block: zhFb as Record<string, unknown>,
  },
};

function getLocale(): Locale {
  return useLocaleStore.getState().locale;
}

function interpolate(template: string, vars?: Record<string, string | number>): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`));
}

function lookupFlat(dict: Record<string, string>, key: string, fallback?: string): string {
  const val = dict[key];
  if (val !== undefined) return val;
  if (fallback !== undefined) return fallback;
  return key;
}

function getNested(obj: Record<string, unknown> | undefined, path: string): unknown {
  if (!obj) return undefined;
  let cur: unknown = obj;
  for (const part of path.split('.')) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return cur;
}

function getModelData(modelId: string): Record<string, unknown> | undefined {
  const locale = getLocale();
  return MODELS[locale][modelId] ?? MODELS.en[modelId];
}

export function t(key: string, vars?: Record<string, string | number>, fallback?: string): string {
  const locale = getLocale();
  const raw = lookupFlat(UI[locale], key, fallback ?? key);
  return interpolate(raw, vars);
}

export function tRuntime(key: string, fallback?: string): string {
  const locale = getLocale();
  return lookupFlat(RUNTIME[locale], key, fallback);
}

export function tMetric(key: string, fallback?: string): string {
  return tRuntime(`metrics.${key}`, fallback ?? key);
}

export function tSeries(name: string, fallback?: string): string {
  return tRuntime(`series.${name}`, fallback ?? name);
}

export function tModel(modelId: string, path: string, fallback?: string): string {
  const locale = getLocale();
  const zhVal = getNested(MODELS.zh[modelId], path);
  if (locale === 'zh' && typeof zhVal === 'string') return zhVal;
  const enVal = getNested(MODELS.en[modelId], path);
  if (typeof enVal === 'string') return enVal;
  return fallback ?? path;
}

export function tModelOptionHelp(
  modelId: string,
  paramName: string,
  optionValue: string,
  fallback?: string,
): string {
  const path = `params.${paramName}.optionsHelp.${optionValue}`;
  const val = getNested(getModelData(modelId), path);
  if (typeof val === 'string' && val) return val;
  return fallback ?? '';
}

export function tDimension(dimension: string): string {
  return tRuntime(`dimension.${dimension}`, dimension);
}

export function tCategory(modelId: string, category: string): string {
  return tModel(modelId, 'category', category);
}
