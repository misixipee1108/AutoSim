import type { Dimension, UnitDef } from './dimensions';

const SUPERSCRIPT_MAP: Record<string, string> = {
  '⁰': '0', '¹': '1', '²': '2', '³': '3', '⁴': '4',
  '⁵': '5', '⁶': '6', '⁷': '7', '⁸': '8', '⁹': '9',
  '⁻': '-', '⁺': '+',
};

export function normalizeUnitSymbol(raw: string): string {
  let s = raw.trim();
  for (const [sup, ascii] of Object.entries(SUPERSCRIPT_MAP)) {
    s = s.split(sup).join(ascii);
  }
  s = s.replace(/\^?\(-?\d+\)/g, (m) => {
    const n = m.match(/-?\d+/)?.[0] ?? '';
    return n.startsWith('-') ? `^${n}` : `^${n}`;
  });
  s = s.replace(/\^(\d+)/g, '^$1');
  s = s.replace(/\s+/g, '');
  s = s.replace(/μ/g, 'u').replace(/µ/g, 'u');
  s = s.replace(/Å/g, 'A').replace(/Å/g, 'A');
  s = s.replace(/g0/g, 'g_0').replace(/g₀/g, 'g_0');
  return s.toLowerCase();
}

const UNIT_DEFS: UnitDef[] = [
  // length (SI base: m)
  { symbol: 'm', dimension: 'length', toSi: 1, aliases: ['meter', 'meters'] },
  { symbol: 'cm', dimension: 'length', toSi: 0.01, aliases: ['centimeter'] },
  { symbol: 'mm', dimension: 'length', toSi: 0.001 },
  { symbol: 'um', dimension: 'length', toSi: 1e-6, aliases: ['µm', 'micrometer', 'micron'] },
  { symbol: 'nm', dimension: 'length', toSi: 1e-9, aliases: ['nanometer'] },
  { symbol: 'km', dimension: 'length', toSi: 1000 },
  { symbol: 'a', dimension: 'length', toSi: 1e-10, aliases: ['angstrom', 'å'] },

  // concentration (SI base: m^-3)
  { symbol: 'm^-3', dimension: 'concentration', toSi: 1, aliases: ['m-3', '/m^3', '1/m^3'] },
  { symbol: 'cm^-3', dimension: 'concentration', toSi: 1e6, aliases: ['cm-3', '/cm^3', '1/cm^3', 'cm^(-3)'] },

  // time (SI base: s)
  { symbol: 's', dimension: 'time', toSi: 1, aliases: ['sec', 'second'] },
  { symbol: 'ms', dimension: 'time', toSi: 1e-3 },
  { symbol: 'us', dimension: 'time', toSi: 1e-6, aliases: ['µs'] },
  { symbol: 'ns', dimension: 'time', toSi: 1e-9 },

  // mass (SI base: kg)
  { symbol: 'kg', dimension: 'mass', toSi: 1 },
  { symbol: 'g', dimension: 'mass', toSi: 0.001 },

  // velocity (SI base: m/s)
  { symbol: 'm/s', dimension: 'velocity', toSi: 1 },
  { symbol: 'km/h', dimension: 'velocity', toSi: 1 / 3.6 },
  { symbol: 'cm/s', dimension: 'velocity', toSi: 0.01 },

  // acceleration (SI base: m/s^2)
  { symbol: 'm/s^2', dimension: 'acceleration', toSi: 1, aliases: ['m/s2', 'm/s²'] },
  { symbol: 'g_0', dimension: 'acceleration', toSi: 9.80665, aliases: ['g0'] },

  // force, energy, voltage, temperature
  { symbol: 'n', dimension: 'force', toSi: 1, aliases: ['newton'] },
  { symbol: 'j', dimension: 'energy', toSi: 1, aliases: ['joule'] },
  { symbol: 'v', dimension: 'voltage', toSi: 1, aliases: ['volt'] },
  { symbol: 'k', dimension: 'temperature', toSi: 1, aliases: ['kelvin'] },

  // compound
  { symbol: 'kg/m', dimension: 'drag_quadratic', toSi: 1 },
  { symbol: 'kg/s', dimension: 'drag_linear', toSi: 1 },
  { symbol: 'v/cm', dimension: 'field', toSi: 100 },
  { symbol: 'f/cm^2', dimension: 'capacitance_area', toSi: 1e4, aliases: ['f/cm2', 'f/cm²'] },
];

const ALIAS_INDEX = new Map<string, UnitDef>();

function registerAlias(alias: string, def: UnitDef) {
  ALIAS_INDEX.set(normalizeUnitSymbol(alias), def);
}

for (const def of UNIT_DEFS) {
  registerAlias(def.symbol, def);
  for (const a of def.aliases ?? []) registerAlias(a, def);
}

export function lookupUnit(symbol: string): UnitDef | undefined {
  return ALIAS_INDEX.get(normalizeUnitSymbol(symbol));
}

export function getDimension(symbol: string): Dimension | undefined {
  return lookupUnit(symbol)?.dimension;
}

export function getCanonicalSymbol(targetUnit: string): string | undefined {
  const def = lookupUnit(targetUnit);
  return def?.symbol;
}

export function listUnitsForDimension(dimension: Dimension): UnitDef[] {
  const seen = new Set<string>();
  const out: UnitDef[] = [];
  for (const def of UNIT_DEFS) {
    if (def.dimension === dimension && !seen.has(def.symbol)) {
      seen.add(def.symbol);
      out.push(def);
    }
  }
  return out;
}

export { UNIT_DEFS };
