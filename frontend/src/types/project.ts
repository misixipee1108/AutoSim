import type { ParameterSchema } from './index';

export interface SimulationProject {
  schema_version: '2.0';
  project_id: string;
  title: string;
  model: Record<string, unknown>;
  studies: Array<Record<string, unknown>>;
  results: {
    output_variables?: Array<Record<string, unknown>>;
    visualizations?: VisualizationRecipe[];
    postprocessing?: unknown[];
    reports?: unknown[];
  };
  active_study_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface VisualizationRecipe {
  viz_id: string;
  chart_type: string;
  tab: { id: string; label: string };
  bindings: {
    x?: string;
    y?: string[];
    x_label?: string;
    y_label?: string;
    log_scale?: boolean;
  };
  implemented?: boolean;
}

export interface ModelTreeNode {
  id: string;
  label: string;
  kind: 'section' | 'node' | 'collection' | 'study' | 'template';
  children?: ModelTreeNode[];
  parameter_refs?: string[];
  study_id?: string;
  study_type?: string;
  interface_id?: string;
  instance_id?: string;
  physics_category?: string;
  parameter_group?: string;
}

export interface ModelTreeSchema {
  schema_version: string;
  roots: ModelTreeNode[];
}

export interface ProjectParameterSchemaResponse {
  tree_path: string;
  parameters: ParameterSchema[];
}
