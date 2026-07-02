/** Physics-field and parameter-group labels for the model tree (mirrors backend physics_tree.py). */

export const PHYSICS_FIELD_LABELS: Record<string, string> = {
  semiconductor: 'Semiconductor',
  mechanics: 'Mechanics',
  thermal: 'Thermal',
  optics: 'Optics',
};

export const GROUP_TREE_LABELS: Record<string, string> = {
  Physics: 'Physics Model',
  Doping: 'Doping',
  Recombination: 'Recombination',
  Body: 'Body',
  Drag: 'Drag',
  Integration: 'Integration',
};

export const GROUP_SLUGS: Record<string, string> = {
  Physics: 'physics',
  Doping: 'doping',
  Recombination: 'recombination',
  Body: 'body',
  Drag: 'drag',
  Integration: 'integration',
};

export const SLUG_TO_GROUP: Record<string, string> = Object.fromEntries(
  Object.entries(GROUP_SLUGS).map(([group, slug]) => [slug, group]),
);

export function physicsFieldLabel(category: string): string {
  return PHYSICS_FIELD_LABELS[category] ?? category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function groupTreeLabel(group: string): string {
  return GROUP_TREE_LABELS[group] ?? group;
}

export function groupSlug(group: string): string {
  return GROUP_SLUGS[group] ?? group.toLowerCase().replace(/\s+/g, '_');
}

export function parsePhysicsInterfaceTreePath(treePath: string): {
  instanceId: string | null;
  groupName: string | null;
} {
  if (!treePath.startsWith('model.physics_interfaces.')) {
    return { instanceId: null, groupName: null };
  }
  const parts = treePath.split('.');
  if (parts.length < 3) return { instanceId: null, groupName: null };
  const instanceId = parts[2];
  if (instanceId.startsWith('template')) return { instanceId: null, groupName: null };
  if (parts.length < 4) return { instanceId, groupName: null };
  return { instanceId, groupName: SLUG_TO_GROUP[parts[3]] ?? null };
}
