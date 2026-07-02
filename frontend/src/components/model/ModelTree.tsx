import { useCallback, useEffect, useRef, useState } from 'react';
import { useAppStore } from '../../store/useAppStore';
import { useLocale, inferModelIdFromProject, resolveProjectTitle } from '../../i18n';
import { ModelTreeNodeView } from './ModelTreeNodeView';
import { getAncestorNodeIds, mergeExpandedIds } from '../../utils/treeExpand';

export function ModelTree() {
  const { t } = useLocale();
  const projectTreeSchema = useAppStore((s) => s.projectTreeSchema);
  const currentProject = useAppStore((s) => s.currentProject);
  const selectedTreePath = useAppStore((s) => s.selectedTreePath);
  const setSelectedTreePath = useAppStore((s) => s.setSelectedTreePath);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());
  const lastProjectIdRef = useRef<string | null>(null);

  const expandLabel = t('projectTree.expandNode', undefined, 'Expand');
  const collapseLabel = t('projectTree.collapseNode', undefined, 'Collapse');

  useEffect(() => {
    if (!selectedTreePath) {
      setExpandedIds(new Set());
      return;
    }
    const ancestors = getAncestorNodeIds(selectedTreePath);
    const projectId = currentProject?.project_id ?? null;
    if (projectId !== lastProjectIdRef.current) {
      lastProjectIdRef.current = projectId;
      setExpandedIds(new Set(ancestors));
      return;
    }
    setExpandedIds((prev) => mergeExpandedIds(prev, ancestors));
  }, [selectedTreePath, currentProject?.project_id]);

  const toggleExpand = useCallback((nodeId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }, []);

  if (!projectTreeSchema || !currentProject) {
    return (
      <div>
        <div className="panel-header">{t('panel.modelTree')}</div>
        <p className="px-3 py-2 text-xs text-muted">{t('panel.loadingProject')}</p>
      </div>
    );
  }

  const modelId = inferModelIdFromProject(currentProject);
  const title = resolveProjectTitle(currentProject.project_id, currentProject.title, modelId);

  return (
    <div>
      <div className="panel-header">{t('panel.modelTree')}</div>
      <div className="px-3 py-1 text-[10px] text-muted truncate" title={title}>
        {title}
      </div>
      <ul className="py-1">
        {projectTreeSchema.roots.map((root) => (
          <ModelTreeNodeView
            key={root.id}
            node={root}
            selectedPath={selectedTreePath}
            expandedIds={expandedIds}
            onSelect={setSelectedTreePath}
            onToggleExpand={toggleExpand}
            expandLabel={expandLabel}
            collapseLabel={collapseLabel}
          />
        ))}
      </ul>
      <div className="px-3 py-2 text-[10px] text-faint border-t border-default">
        {t('projectTree.schemaVersion')}
      </div>
    </div>
  );
}
