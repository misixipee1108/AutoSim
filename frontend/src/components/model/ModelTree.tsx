import { useAppStore } from '../../store/useAppStore';
import { useLocale, tModel, tCategory, tDimension } from '../../i18n';

export function ModelTree() {
  const { t } = useLocale();
  const descriptor = useAppStore((s) => s.currentDescriptor);
  const selected = useAppStore((s) => s.selectedTreeNode);
  const setSelected = useAppStore((s) => s.setSelectedTreeNode);

  if (!descriptor) return null;

  return (
    <div>
      <div className="panel-header">{t('panel.modelTree')}</div>
      <ul className="py-1">
        {descriptor.tree_nodes.map((node) => (
          <li key={node.id}>
            <button
              type="button"
              onClick={() => setSelected(node.id)}
              className={`w-full text-left px-3 py-1.5 text-xs transition-colors tree-item ${
                selected === node.id ? 'tree-item-active' : ''
              }`}
            >
              {tModel(descriptor.model_id, `tree.${node.id}`, node.label)}
            </button>
          </li>
        ))}
      </ul>
      <div className="px-3 py-2 text-[10px] text-faint border-t border-default">
        {tCategory(descriptor.model_id, descriptor.category)} · {tDimension(descriptor.dimension)}
      </div>
    </div>
  );
}
