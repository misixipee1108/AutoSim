import type { ModelTreeNode } from '../../types/project';
import { resolveTreeLabel } from '../../i18n';

interface ModelTreeNodeViewProps {
  node: ModelTreeNode;
  selectedPath: string | null;
  expandedIds: Set<string>;
  onSelect: (path: string) => void;
  onToggleExpand: (nodeId: string) => void;
  expandLabel: string;
  collapseLabel: string;
  depth?: number;
}

export function ModelTreeNodeView({
  node,
  selectedPath,
  expandedIds,
  onSelect,
  onToggleExpand,
  expandLabel,
  collapseLabel,
  depth = 0,
}: ModelTreeNodeViewProps) {
  const hasChildren = Boolean(node.children?.length);
  const isExpanded = hasChildren && expandedIds.has(node.id);
  const isSelected = selectedPath === node.id;
  const displayLabel = resolveTreeLabel(node.id, node.label, {
    studyType: node.study_type,
    interfaceId: node.interface_id,
    physicsCategory: node.physics_category,
    parameterGroup: node.parameter_group,
  });
  const padding = 8 + depth * 14;

  return (
    <li>
      <div
        className={`flex items-stretch min-h-[28px] tree-item ${isSelected ? 'tree-item-active' : ''}`}
        style={{ paddingLeft: padding, paddingRight: 8 }}
      >
        {hasChildren ? (
          <button
            type="button"
            aria-expanded={isExpanded}
            aria-label={isExpanded ? collapseLabel : expandLabel}
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand(node.id);
            }}
            className="tree-toggle shrink-0"
          >
            <span className={`tree-chevron ${isExpanded ? 'tree-chevron-expanded' : ''}`} aria-hidden>
              ▶
            </span>
          </button>
        ) : (
          <span className="tree-toggle-spacer shrink-0" aria-hidden />
        )}
        <button
          type="button"
          onClick={() => onSelect(node.id)}
          className={`flex-1 text-left py-1.5 text-xs transition-colors ${
            node.kind === 'section' ? 'font-semibold text-primary' : 'text-primary'
          }`}
        >
          {displayLabel}
        </button>
      </div>
      {hasChildren && isExpanded ? (
        <ul>
          {node.children!.map((child) => (
            <ModelTreeNodeView
              key={child.id}
              node={child}
              selectedPath={selectedPath}
              expandedIds={expandedIds}
              onSelect={onSelect}
              onToggleExpand={onToggleExpand}
              expandLabel={expandLabel}
              collapseLabel={collapseLabel}
              depth={depth + 1}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}
