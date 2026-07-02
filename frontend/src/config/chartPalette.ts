/** Unified series colors for physics charts (dark/light compatible). */
export const CHART_SERIES_COLORS: Record<string, string> = {
  potential: '#3b82f6',
  electric_field: '#f59e0b',
  electron_density: '#22c55e',
  hole_density: '#ef4444',
  charge_density: '#a855f7',
  residual: '#94a3b8',
  scaled_residual: '#38bdf8',
  scaled_delta: '#c084fc',
  position: '#3b82f6',
  velocity: '#f59e0b',
  energy_drift: '#ef4444',
};

export const CHART_ANIMATION = {
  duration: 800,
  easing: 'cubicOut' as const,
  delayStep: 120,
};

export function seriesColor(name: string): string {
  return CHART_SERIES_COLORS[name] ?? '#64748b';
}
