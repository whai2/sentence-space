import { useQuery } from "@tanstack/react-query";
import { KnowledgeGraphApi } from "./knowledgeGraphApi";
import type { GraphData, NodeDetail } from "../types";

export const knowledgeGraphKeys = {
  all: ["knowledge-graph"] as const,
  graph: () => [...knowledgeGraphKeys.all, "graph"] as const,
  node: (nodeId: string) =>
    [...knowledgeGraphKeys.all, "node", nodeId] as const,
};

export const useKnowledgeGraphData = () => {
  const api = new KnowledgeGraphApi();
  return useQuery<GraphData>({
    queryKey: knowledgeGraphKeys.graph(),
    queryFn: () => api.getGraph(),
  });
};

export const useNodeDetail = (nodeId: string | null) => {
  const api = new KnowledgeGraphApi();
  return useQuery<NodeDetail>({
    queryKey: knowledgeGraphKeys.node(nodeId ?? ""),
    queryFn: () => api.getNodeDetail(nodeId!),
    enabled: !!nodeId,
  });
};
