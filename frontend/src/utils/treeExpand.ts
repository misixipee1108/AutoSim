/** Return ancestor node ids for a dotted tree path (e.g. model.geometry → ['model']). */
export function getAncestorNodeIds(nodeId: string): string[] {
  const parts = nodeId.split('.');
  const ancestors: string[] = [];
  for (let i = 1; i < parts.length; i++) {
    ancestors.push(parts.slice(0, i).join('.'));
  }
  return ancestors;
}

export function mergeExpandedIds(current: Set<string>, nodeIds: Iterable<string>): Set<string> {
  const next = new Set(current);
  for (const id of nodeIds) next.add(id);
  return next;
}
