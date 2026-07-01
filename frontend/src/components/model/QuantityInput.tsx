import { useCallback, useEffect, useState } from 'react';
import type { ParameterSchema } from '../../types';
import { useAppStore } from '../../store/useAppStore';
import { useLocale } from '../../i18n';
import { parseQuantity, toCanonical } from '../../units';
import { DelayedTooltip } from '../ui/DelayedTooltip';

interface Props {
  param: ParameterSchema;
  label: string;
  description: string;
}

export function QuantityInput({ param, label, description }: Props) {
  const { t } = useLocale();
  const canonicalValue = useAppStore((s) => {
    const parts = param.name.split('.');
    let cur: unknown = s.config;
    for (const p of parts) {
      if (cur == null || typeof cur !== 'object') return undefined;
      cur = (cur as Record<string, unknown>)[p];
    }
    return cur;
  });
  const displayText = useAppStore((s) => s.quantityDisplay[param.name]);
  const setConfigValue = useAppStore((s) => s.setConfigValue);
  const setQuantityDisplay = useAppStore((s) => s.setQuantityDisplay);

  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (displayText !== undefined) {
      setText(displayText);
    } else if (typeof canonicalValue === 'number' && param.unit) {
      setText(`${canonicalValue}[${param.unit}]`);
    }
  }, [displayText, canonicalValue, param.unit, param.name]);

  const commit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed) {
      setError(t('unit.invalid'));
      return;
    }

    const parsed = parseQuantity(trimmed);
    if (!parsed.ok) {
      setError(t('unit.invalid'));
      return;
    }

    const targetUnit = param.unit ?? '';
    let canonical: number;

    if (parsed.quantity.unit) {
      const conv = toCanonical(parsed.quantity.value, parsed.quantity.unit, targetUnit);
      if (!conv.ok) {
        setError(conv.error === 'dimension_mismatch' ? t('unit.dimensionMismatch') : t('unit.invalid'));
        return;
      }
      canonical = conv.value;
    } else if (targetUnit) {
      canonical = parsed.quantity.value;
    } else {
      canonical = parsed.quantity.value;
    }

    if (param.min !== undefined && canonical < param.min) {
      setError(t('unit.outOfRange'));
      return;
    }
    if (param.max !== undefined && canonical > param.max) {
      setError(t('unit.outOfRange'));
      return;
    }

    setError(null);
    setConfigValue(param.name, param.type === 'integer' ? Math.round(canonical) : canonical);
    setQuantityDisplay(param.name, trimmed);
  }, [text, param, setConfigValue, setQuantityDisplay, t]);

  const placeholder = param.default !== undefined && param.unit
    ? `${param.default}[${param.unit}]`
    : param.unit
      ? t('unit.placeholder', { unit: param.unit })
      : '';

  return (
    <label className="flex flex-col gap-1">
      <DelayedTooltip content={description}>
        <span className="text-[11px] text-muted cursor-help">
          {label}
          {param.unit && (
            <span className="text-faint ml-1">
              ({t('unit.canonicalHint', { unit: param.unit })})
            </span>
          )}
        </span>
      </DelayedTooltip>
      <input
        type="text"
        className={`font-mono text-xs ${error ? 'border-red-500' : ''}`}
        value={text}
        placeholder={placeholder}
        onChange={(e) => {
          setText(e.target.value);
          setError(null);
        }}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.currentTarget.blur();
          }
        }}
      />
      {error && <span className="text-[10px] text-red-400">{error}</span>}
    </label>
  );
}
