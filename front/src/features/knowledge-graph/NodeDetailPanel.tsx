import styled from "@emotion/styled";
import type { NodeDetail, NodeType } from "./types";
import { NODE_COLORS } from "./types";

interface NodeDetailPanelProps {
  detail: NodeDetail | undefined;
  isLoading: boolean;
  onClose: () => void;
}

const Panel = styled.div`
  width: 320px;
  background: #252536;
  border-left: 1px solid #333;
  border-radius: 0 8px 8px 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

const PanelHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #333;
`;

const HeaderLeft = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
`;

const TypeBadge = styled.span<{ nodeType: string }>`
  background: ${(p) => NODE_COLORS[p.nodeType as NodeType] || "#666"};
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
`;

const NodeName = styled.span`
  color: #eee;
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  color: #888;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  &:hover {
    color: #fff;
  }
`;

const PanelBody = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 16px;
`;

const SectionTitle = styled.h4`
  color: #aaa;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 8px 0;
`;

const PropsTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
`;

const PropRow = styled.tr`
  &:not(:last-child) td {
    border-bottom: 1px solid #2a2a3e;
  }
`;

const PropKey = styled.td`
  color: #888;
  font-size: 12px;
  padding: 6px 8px 6px 0;
  white-space: nowrap;
  vertical-align: top;
  width: 110px;
`;

const PropValue = styled.td`
  color: #ddd;
  font-size: 12px;
  padding: 6px 0;
  word-break: break-all;
`;

const ConnectionItem = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  &:not(:last-child) {
    border-bottom: 1px solid #2a2a3e;
  }
`;

const Arrow = styled.span`
  color: #888;
  font-size: 12px;
  min-width: 16px;
  text-align: center;
`;

const RelBadge = styled.span`
  background: #333;
  color: #aaa;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  white-space: nowrap;
`;

const NeighborName = styled.span`
  color: #ccc;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const NeighborBadge = styled.span<{ nodeType: string }>`
  background: ${(p) => NODE_COLORS[p.nodeType as NodeType] || "#666"}33;
  color: ${(p) => NODE_COLORS[p.nodeType as NodeType] || "#666"};
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
`;

const LoadingText = styled.div`
  color: #888;
  font-size: 13px;
  text-align: center;
  padding: 40px 0;
`;

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string") {
    // truncate long strings
    return value.length > 120 ? value.slice(0, 117) + "..." : value;
  }
  return String(value);
}

export const NodeDetailPanel = ({
  detail,
  isLoading,
  onClose,
}: NodeDetailPanelProps) => {
  if (isLoading) {
    return (
      <Panel>
        <PanelHeader>
          <span style={{ color: "#aaa", fontSize: 13 }}>Loading...</span>
          <CloseButton onClick={onClose}>&times;</CloseButton>
        </PanelHeader>
        <PanelBody>
          <LoadingText>Loading node details...</LoadingText>
        </PanelBody>
      </Panel>
    );
  }

  if (!detail) return null;

  const propEntries = Object.entries(detail.properties).filter(
    ([key]) => !["__typename"].includes(key)
  );

  return (
    <Panel>
      <PanelHeader>
        <HeaderLeft>
          <TypeBadge nodeType={detail.label}>{detail.label}</TypeBadge>
          <NodeName title={detail.name}>{detail.name || detail.id}</NodeName>
        </HeaderLeft>
        <CloseButton onClick={onClose}>&times;</CloseButton>
      </PanelHeader>
      <PanelBody>
        {/* Properties */}
        <SectionTitle>Properties</SectionTitle>
        <PropsTable>
          <tbody>
            {propEntries.map(([key, value]) => (
              <PropRow key={key}>
                <PropKey>{key}</PropKey>
                <PropValue>{formatValue(value)}</PropValue>
              </PropRow>
            ))}
            {propEntries.length === 0 && (
              <PropRow>
                <PropValue colSpan={2} style={{ color: "#666" }}>
                  No properties
                </PropValue>
              </PropRow>
            )}
          </tbody>
        </PropsTable>

        {/* Connections */}
        <SectionTitle>
          Connections ({detail.neighbors.length})
        </SectionTitle>
        {detail.neighbors.length === 0 ? (
          <div style={{ color: "#666", fontSize: 12 }}>No connections</div>
        ) : (
          detail.neighbors.map((neighbor, idx) => (
            <ConnectionItem key={`${neighbor.id}-${idx}`}>
              <Arrow>
                {neighbor.direction === "outgoing" ? "\u2192" : "\u2190"}
              </Arrow>
              <RelBadge>{neighbor.relationship}</RelBadge>
              <NeighborBadge nodeType={neighbor.label}>
                {neighbor.label}
              </NeighborBadge>
              <NeighborName title={neighbor.name}>
                {neighbor.name || neighbor.id}
              </NeighborName>
            </ConnectionItem>
          ))
        )}
      </PanelBody>
    </Panel>
  );
};
