import { describe, it, expect } from 'vitest';
import { parseQuantity } from './parse';
import { convert, toCanonical } from './convert';

describe('parseQuantity', () => {
  it('parses value with bracket unit', () => {
    const r = parseQuantity('10[nm]');
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.quantity.value).toBe(10);
      expect(r.quantity.unit).toBe('nm');
    }
  });

  it('parses scientific notation with unit', () => {
    const r = parseQuantity('1e18[cm-3]');
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.quantity.value).toBe(1e18);
  });

  it('parses plain number without unit', () => {
    const r = parseQuantity('300');
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.quantity.value).toBe(300);
      expect(r.quantity.unit).toBe('');
    }
  });

  it('rejects invalid input', () => {
    expect(parseQuantity('abc[nm]').ok).toBe(false);
    expect(parseQuantity('').ok).toBe(false);
  });
});

describe('convert', () => {
  it('converts 10 nm to cm', () => {
    const r = convert(10, 'nm', 'cm');
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value).toBeCloseTo(1e-6, 12);
  });

  it('converts 200 nm to cm for PN geometry', () => {
    const r = toCanonical(200, 'nm', 'cm');
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value).toBeCloseTo(2e-5, 12);
  });

  it('converts 100 km to m', () => {
    const r = toCanonical(100, 'km', 'm');
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value).toBeCloseTo(1e5, 6);
  });

  it('300 K is identity', () => {
    const r = toCanonical(300, 'K', 'K');
    expect(r.ok).toBe(true);
    if (r.ok) expect(r.value).toBe(300);
  });

  it('rejects dimension mismatch', () => {
    const r = convert(10, 'kg', 'cm');
    expect(r.ok).toBe(false);
  });
});
