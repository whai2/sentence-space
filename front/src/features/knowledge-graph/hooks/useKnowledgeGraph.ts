import { useState, useCallback } from "react";

export const useKnowledgeGraph = () => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const selectNode = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedNodeId(null);
  }, []);

  return {
    selectedNodeId,
    selectNode,
    clearSelection,
  };
};
