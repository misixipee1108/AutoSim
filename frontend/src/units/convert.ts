import { getDimension, lookupUnit } from './registry';

export type ConvertError = 'unknown_unit' | 'dimension_mismatch';

export type ConvertResult =
  | { ok: true; value: number }
  | { ok: false; error: ConvertError };

export function convert(value: number, fromUnit: string, toUnit: string): ConvertResult {
  const from = lookupUnit(fromUnit);
  const to = lookupUnit(toUnit);
  if (!from || !to) return { ok: false, error: 'unknown_unit' };
  if (from.dimension !== to.dimension) return { ok: false, error: 'dimension_mismatch' };
  const si = value * from.toSi;
  return { ok: true, value: si / to.toSi };
}

export function toCanonical(value: number, fromUnit: string, targetUnit: string): ConvertResult {
  if (!fromUnit) {
    const target = lookupUnit(targetUnit);
    if (!target) return { ok: false, error: 'unknown_unit' };
    return { ok: true, value };
  }
  return convert(value, fromUnit, targetUnit);
}

export function assertSameDimension(fromUnit: string, targetUnit: string): boolean {
  const from = lookupUnit(fromUnit);
  const to = lookupUnit(targetUnit);
  if (!from || !to) return false;
  return from.dimension === to.dimension;
}

export function resolveTargetDimension(targetUnit: string) {
  return getDimension(targetUnit);
}
