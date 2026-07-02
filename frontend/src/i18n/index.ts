import { useLocaleStore } from './localeStore';
import {
  t,
  tCategory,
  tDimension,
  tMetric,
  tModel,
  tModelOptionHelp,
  tRuntime,
  tSeries,
} from './translations';

export {
  t,
  tRuntime,
  tMetric,
  tSeries,
  tModel,
  tModelOptionHelp,
  tDimension,
  tCategory,
};

export {
  inferModelIdFromProject,
  inferModelIdFromRun,
  paramPathToI18nKey,
  resolveActionRaw,
  resolveAgentReason,
  resolveAxisLabel,
  resolveChartTabLabel,
  resolveEnum,
  resolveMetricKey,
  resolveParamDescription,
  resolveParamGroup,
  resolveParamLabel,
  resolveParamKey,
  resolveParamOption,
  resolveParamOptionHelp,
  resolveProbeLabel,
  resolveProjectTitle,
  resolveStudyLabelFromProject,
  resolveTemplateTitle,
  resolveTreeLabel,
  resolveValidationReason,
} from './resolveLabels';

export type { PhysicsModelId } from './resolveLabels';

export function useLocale() {
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);
  return {
    locale,
    setLocale,
    t,
    tModel,
    tModelOptionHelp,
    tRuntime,
    tMetric,
    tSeries,
    tDimension,
    tCategory,
  };
}

export { initLocale, useLocaleStore } from './localeStore';
export type { Locale } from './types';
