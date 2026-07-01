export type Dimension =
  | 'length'
  | 'concentration'
  | 'time'
  | 'mass'
  | 'velocity'
  | 'acceleration'
  | 'force'
  | 'energy'
  | 'voltage'
  | 'temperature'
  | 'drag_quadratic'
  | 'drag_linear'
  | 'field'
  | 'capacitance_area'
  | 'dimensionless';

export interface UnitDef {
  symbol: string;
  dimension: Dimension;
  /** Multiplier to convert 1 of this unit into the dimension SI base. */
  toSi: number;
  aliases?: string[];
}
