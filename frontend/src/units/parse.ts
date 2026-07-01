import { lookupUnit, normalizeUnitSymbol } from './registry';

export interface ParsedQuantity {
  value: number;
  unit: string;
}

export type ParseError = 'invalid' | 'empty';

export type ParseResult =
  | { ok: true; quantity: ParsedQuantity }
  | { ok: false; error: ParseError };

const QUANTITY_RE = /^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(?:\[(.+)\])?\s*$/;

export function parseQuantity(text: string): ParseResult {
  const trimmed = text.trim();
  if (!trimmed) return { ok: false, error: 'empty' };

  const match = trimmed.match(QUANTITY_RE);
  if (!match) return { ok: false, error: 'invalid' };

  const value = Number(match[1]);
  if (!Number.isFinite(value)) return { ok: false, error: 'invalid' };

  const unitRaw = match[2]?.trim();
  if (!unitRaw) {
    return { ok: true, quantity: { value, unit: '' } };
  }

  const unit = normalizeUnitSymbol(unitRaw);
  if (!lookupUnit(unitRaw) && !lookupUnit(unit)) {
    return { ok: false, error: 'invalid' };
  }

  const def = lookupUnit(unitRaw) ?? lookupUnit(unit);
  return { ok: true, quantity: { value, unit: def!.symbol } };
}

export function formatQuantityDisplay(value: number, unit: string): string {
  if (!unit) return String(value);
  const displayUnit = unit.includes('^') ? unit.replace(/\^(-?\d+)/g, '⁻$1').replace(/-3/g, '³').replace(/-2/g, '²') : unit;
  const v = Math.abs(value) >= 1e6 || (Math.abs(value) < 1e-3 && value !== 0)
    ? value.toExponential()
    : String(value);
  return `${v}[${displayUnit}]`;
}
