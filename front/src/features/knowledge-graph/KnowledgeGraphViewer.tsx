import { useRef, useEffect, useCallback } from "react";
import ForceGraph2D, {
  type ForceGraphMethods,
} from "react-force-graph-2d";
import styled from "@emotion/styled";
import type { GraphData, GraphNode, NodeType } from "./types";
import { NODE_COLORS, NODE_SIZES } from "./types";

interface KnowledgeGraphViewerProps {
  data: GraphData;
  selectedNodeId: string | null;
  onNodeClick: (nodeId: string) => void;
  width: number;
  height: number;
}

const Container = styled.div`
  position: relative;
  background: #1a1a2e;
  border-radius: 8px;
  overflow: hidden;
`;

const Legend = styled.div`
  position: absolute;
  top: 12px;
  left: 12px;
  background: rgba(30, 30, 46, 0.9);
  border: 1px solid #333;
  border-radius: 6px;
  padding: 10px 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  z-index: 10;
`;

const LegendItem = styled.div`
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #ccc;
`;

const LegendDot = styled.span<{ color: string }>`
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: ${(p) => p.color};
  display: inline-block;
`;

const LEGEND_ENTRIES: { label: string; type: NodeType }[] = [
  { label: "Query", type: "Query" },
  { label: "Topic", type: "Topic" },
  { label: "Keyword", type: "Keyword" },
  { label: "Agent", type: "Agent" },
  { label: "Tool", type: "Tool" },
  { label: "ToolExecution", type: "ToolExecution" },
];

export const KnowledgeGraphViewer = ({
  data,
  selectedNodeId,
  onNodeClick,
  width,
  height,
}: KnowledgeGraphViewerProps) => {
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);

  useEffect(() => {
    if (fgRef.current) {
      // 노드 간 거리를 넓힘
      fgRef.current.d3Force("link")?.distance(180);
      fgRef.current.d3Force("charge")?.strength(-500);

      if (data.nodes.length > 0) {
        setTimeout(() => {
          fgRef.current?.zoomToFit(400, 60);
        }, 500);
      }
    }
  }, [data]);

  const nodeCanvasObject = useCallback(
    (node: GraphNode & { x?: number; y?: number }, ctx: CanvasRenderingContext2D) => {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const label = node.label as NodeType;
      const color = NODE_COLORS[label] || "#999";
      const size = NODE_SIZES[label] || 5;
      const isSelected = node.id === selectedNodeId;

      // selection ring
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(x, y, size + 4, 0, 2 * Math.PI);
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 2.5;
        ctx.stroke();
      }

      // node circle
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // label text
      const displayName = node.name || label;
      const truncated =
        displayName.length > 16
          ? displayName.slice(0, 14) + "..."
          : displayName;
      ctx.font = `${isSelected ? "bold " : ""}8px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = "#ddd";
      ctx.fillText(truncated, x, y + size + 6);
    },
    [selectedNodeId]
  );

  const linkCanvasObject = useCallback(
    (
      link: {
        source: GraphNode & { x?: number; y?: number };
        target: GraphNode & { x?: number; y?: number };
        relationship?: string;
      },
      ctx: CanvasRenderingContext2D,
      globalScale: number
    ) => {
      const source = link.source;
      const target = link.target;
      if (!source?.x || !target?.x) return;

      ctx.beginPath();
      ctx.moveTo(source.x, source.y!);
      ctx.lineTo(target.x, target.y!);
      ctx.strokeStyle = "rgba(255,255,255,0.15)";
      ctx.lineWidth = 0.8;
      ctx.stroke();

      // show relationship label when zoomed in
      if (globalScale > 2 && link.relationship) {
        const midX = (source.x + target.x) / 2;
        const midY = (source.y! + target.y!) / 2;
        ctx.font = "8px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "rgba(255,255,255,0.5)";
        ctx.fillText(link.relationship, midX, midY);
      }
    },
    []
  );

  return (
    <Container>
      <Legend>
        {LEGEND_ENTRIES.map((entry) => (
          <LegendItem key={entry.type}>
            <LegendDot color={NODE_COLORS[entry.type]} />
            {entry.label}
          </LegendItem>
        ))}
      </Legend>
      <ForceGraph2D
        ref={fgRef}
        width={width}
        height={height}
        graphData={data}
        nodeId="id"
        nodeCanvasObject={nodeCanvasObject as any}
        linkCanvasObject={linkCanvasObject as any}
        onNodeClick={(node: any) => onNodeClick(node.id)}
        backgroundColor="#1a1a2e"
        linkDirectionalArrowLength={5}
        linkDirectionalArrowRelPos={1}
        cooldownTicks={100}
        d3VelocityDecay={0.3}
        d3AlphaDecay={0.02}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          const size = NODE_SIZES[(node.label as NodeType)] || 10;
          ctx.beginPath();
          ctx.arc(node.x, node.y, size + 6, 0, 2 * Math.PI);
          ctx.fillStyle = color;
          ctx.fill();
        }}
      />
    </Container>
  );
};
