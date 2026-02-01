import { useRef, useState, useEffect } from "react";
import styled from "@emotion/styled";
import {
  KnowledgeGraphViewer,
  NodeDetailPanel,
  useKnowledgeGraph,
  useKnowledgeGraphData,
  useNodeDetail,
} from "../../features/knowledge-graph";

const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e2e;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 1px solid #333;
  background: #252536;
`;

const HeaderLeft = styled.div`
  display: flex;
  align-items: center;
  gap: 16px;
`;

const Title = styled.h2`
  color: #eee;
  font-size: 16px;
  font-weight: 600;
  margin: 0;
`;

const Stats = styled.span`
  color: #888;
  font-size: 13px;
`;

const RefreshButton = styled.button`
  background: #333;
  border: 1px solid #444;
  color: #ccc;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  &:hover {
    background: #444;
    color: #fff;
  }
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const Body = styled.div`
  flex: 1;
  display: flex;
  overflow: hidden;
`;

const GraphArea = styled.div`
  flex: 1;
  position: relative;
`;

const EmptyState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
  gap: 12px;
`;

const EmptyIcon = styled.div`
  font-size: 48px;
  opacity: 0.4;
`;

const ErrorBanner = styled.div`
  padding: 12px 20px;
  background: rgba(244, 67, 54, 0.1);
  border-bottom: 1px solid rgba(244, 67, 54, 0.3);
  color: #f44336;
  font-size: 13px;
`;

export const KnowledgeGraphPage = () => {
  const { selectedNodeId, selectNode, clearSelection } = useKnowledgeGraph();
  const { data, isLoading, error, refetch, isFetching } =
    useKnowledgeGraphData();
  const { data: nodeDetail, isLoading: nodeDetailLoading } =
    useNodeDetail(selectedNodeId);

  const graphAreaRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    const updateDimensions = () => {
      if (graphAreaRef.current) {
        const rect = graphAreaRef.current.getBoundingClientRect();
        setDimensions({ width: rect.width, height: rect.height });
      }
    };

    updateDimensions();
    const observer = new ResizeObserver(updateDimensions);
    if (graphAreaRef.current) observer.observe(graphAreaRef.current);
    return () => observer.disconnect();
  }, []);

  const graphData = data ?? { nodes: [], links: [] };
  const hasData = graphData.nodes.length > 0;

  return (
    <PageContainer>
      <Header>
        <HeaderLeft>
          <Title>Knowledge Graph</Title>
          {hasData && (
            <Stats>
              {graphData.nodes.length} nodes / {graphData.links.length} links
            </Stats>
          )}
        </HeaderLeft>
        <RefreshButton
          onClick={() => refetch()}
          disabled={isFetching}
        >
          {isFetching ? "Loading..." : "Refresh"}
        </RefreshButton>
      </Header>

      {error && (
        <ErrorBanner>
          Failed to load graph data: {(error as Error).message}
        </ErrorBanner>
      )}

      <Body>
        <GraphArea ref={graphAreaRef}>
          {isLoading ? (
            <EmptyState>
              <div>Loading graph...</div>
            </EmptyState>
          ) : !hasData ? (
            <EmptyState>
              <EmptyIcon>&#9673;</EmptyIcon>
              <div>No graph data yet</div>
              <div style={{ fontSize: 12 }}>
                Start chatting with the multi-agent to build the knowledge graph
              </div>
            </EmptyState>
          ) : (
            <KnowledgeGraphViewer
              data={graphData}
              selectedNodeId={selectedNodeId}
              onNodeClick={selectNode}
              width={dimensions.width}
              height={dimensions.height}
            />
          )}
        </GraphArea>

        {selectedNodeId && (
          <NodeDetailPanel
            detail={nodeDetail}
            isLoading={nodeDetailLoading}
            onClose={clearSelection}
          />
        )}
      </Body>
    </PageContainer>
  );
};
