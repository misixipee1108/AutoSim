import { formatQuantityDisplay } from './parse';

export function formatCanonical(value: number, canonicalUnit: string): string {
  return formatQuantityDisplay(value, canonicalUnit);
}
