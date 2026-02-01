export interface GraphNode {
  id: string;
  label: string;
  name: string;
  properties: Record<string, unknown>;
}

export interface GraphLink {
  source: string;
  target: string;
  relationship: string;
  properties: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface NodeNeighbor {
  id: string;
  label: string;
  name: string;
  relationship: string;
  direction: "incoming" | "outgoing";
}

export interface NodeDetail {
  id: string;
  label: string;
  name: string;
  properties: Record<string, unknown>;
  neighbors: NodeNeighbor[];
}

export type NodeType =
  | "Query"
  | "Topic"
  | "Keyword"
  | "Agent"
  | "Tool"
  | "ToolExecution";

export const NODE_COLORS: Record<NodeType, string> = {
  Query: "#4a9eff",
  Topic: "#4caf50",
  Keyword: "#ffd740",
  Agent: "#ab47bc",
  Tool: "#ff9800",
  ToolExecution: "#78909c",
};

export const NODE_SIZES: Record<NodeType, number> = {
  Query: 16,
  Topic: 12,
  Keyword: 9,
  Agent: 20,
  Tool: 14,
  ToolExecution: 10,
};
