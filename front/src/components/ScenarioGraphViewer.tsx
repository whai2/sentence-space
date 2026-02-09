import { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import './ScenarioGraphViewer.css';

interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
}

interface GraphEdge {
  id: string;
  from_id: string;
  to_id: string;
  type: string;
  properties: Record<string, any>;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface Scenario {
  id: string;
  title: string;
  difficulty: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ScenarioGraphViewer() {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphContentRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState(480);
  const [isResizing, setIsResizing] = useState(false);

  // 시나리오 목록 로드
  useEffect(() => {
    const loadScenarios = async () => {
      try {
        const response = await fetch(`${API_URL}/api/graph/scenarios/list`);
        if (!response.ok) throw new Error('Failed to load scenarios');
        const data = await response.json();
        setScenarios(data);
        if (data.length > 0) {
          setSelectedScenario(data[0].id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      }
    };
    loadScenarios();
  }, []);

  // 사이드바 리사이징 핸들러
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing || !graphContentRef.current) return;

      const containerRect = graphContentRef.current.getBoundingClientRect();
      const newWidth = containerRect.right - e.clientX;

      // 최소 300px, 최대 800px
      if (newWidth >= 300 && newWidth <= 800) {
        setSidebarWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'ew-resize';
      document.body.style.userSelect = 'none';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing]);

  // 그래프 렌더링
  useEffect(() => {
    if (!selectedScenario || !containerRef.current) return;

    const loadGraph = async () => {
      setLoading(true);
      setError('');

      try {
        const response = await fetch(
          `${API_URL}/api/graph/scenarios?scenario_id=${selectedScenario}`
        );
        if (!response.ok) throw new Error('Failed to load graph data');
        const graphData: GraphData = await response.json();

        // vis-network 데이터 형식으로 변환
        const nodes = graphData.nodes.map((node) => ({
          id: node.id,
          label: node.label,
          title: `${node.type}\n${JSON.stringify(node.properties, null, 2)}`,
          color: getNodeColor(node.type),
          font: { size: 14 },
          shape: getNodeShape(node.type),
        }));

        const edges = graphData.edges.map((edge) => ({
          from: edge.from_id,
          to: edge.to_id,
          label: edge.type,
          arrows: 'to',
          font: { size: 10, align: 'middle' },
        }));

        // 기존 네트워크 제거
        if (networkRef.current) {
          networkRef.current.destroy();
        }

        // 새 네트워크 생성
        if (!containerRef.current) return;
        const network = new Network(
          containerRef.current,
          { nodes, edges },
          {
            nodes: {
              borderWidth: 2,
              borderWidthSelected: 4,
              font: {
                color: '#ffffff',
                size: 14,
              },
            },
            edges: {
              color: {
                color: '#848484',
                highlight: '#ff9500',
              },
              smooth: {
                type: 'cubicBezier',
                forceDirection: 'horizontal',
                roundness: 0.4,
              },
            },
            physics: {
              enabled: true,
              stabilization: {
                iterations: 200,
              },
              barnesHut: {
                gravitationalConstant: -8000,
                springConstant: 0.04,
                springLength: 95,
              },
            },
            interaction: {
              hover: true,
              tooltipDelay: 100,
            },
          }
        );

        // 노드 클릭 이벤트 핸들러
        network.on('click', (params) => {
          if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const clickedNode = graphData.nodes.find((n) => n.id === nodeId);
            if (clickedNode) {
              setSelectedNode(clickedNode);
            }
          } else {
            setSelectedNode(null);
          }
        });

        networkRef.current = network;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    loadGraph();

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [selectedScenario]);

  return (
    <div className="graph-viewer">
      <div className="graph-controls">
        <label>
          시나리오 선택:
          <select
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value)}
            disabled={loading}
          >
            {scenarios.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>
                {scenario.title} ({scenario.difficulty})
              </option>
            ))}
          </select>
        </label>
        {loading && <span className="loading">로딩 중...</span>}
        {error && <span className="error">{error}</span>}
      </div>
      <div className="graph-content" ref={graphContentRef}>
        <div ref={containerRef} className="graph-container" />
        {selectedNode && (
          <>
            <div
              className="resize-handle"
              onMouseDown={() => setIsResizing(true)}
            />
            <div className="node-details" style={{ width: `${sidebarWidth}px` }}>
            <div className="details-header">
              <h3>{selectedNode.label}</h3>
              <button
                className="close-button"
                onClick={() => setSelectedNode(null)}
              >
                ✕
              </button>
            </div>
            <div className="details-body">
              <div className="detail-item">
                <span className="detail-label">타입:</span>
                <span className={`detail-value type-badge ${selectedNode.type.toLowerCase()}`}>
                  {selectedNode.type}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">ID:</span>
                <span className="detail-value">{selectedNode.id}</span>
              </div>

              {/* Rule 타입인 경우 특별 처리 */}
              {selectedNode.type === 'Rule' && (
                <>
                  <div className="detail-item">
                    <span className="detail-label">규칙 유형:</span>
                    <span className={`detail-value rule-type ${selectedNode.properties.rule_type}`}>
                      {getRuleTypeLabel(selectedNode.properties.rule_type)}
                    </span>
                  </div>
                  <div className="detail-item full-width">
                    <span className="detail-label">설명:</span>
                    <p className="detail-description">{selectedNode.properties.description}</p>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">중요도:</span>
                    <span className="detail-value">
                      {selectedNode.properties.importance}/10
                    </span>
                  </div>
                  <div className="detail-item">
                    <span className="detail-label">공개 여부:</span>
                    <span className={`detail-value ${selectedNode.properties.is_hidden ? 'hidden' : 'visible'}`}>
                      {selectedNode.properties.is_hidden ? '🔐 숨김 (김독자만 알고 있음)' : '👁️ 공개'}
                    </span>
                  </div>
                </>
              )}

              {/* 기타 속성들 */}
              <div className="detail-item full-width">
                <span className="detail-label">전체 속성:</span>
                <pre className="properties-json">
                  {JSON.stringify(selectedNode.properties, null, 2)}
                </pre>
              </div>
            </div>
          </div>
          </>
        )}
      </div>
    </div>
  );
}

// Rule 타입 라벨 변환
function getRuleTypeLabel(ruleType: string): string {
  const labels: Record<string, string> = {
    win_condition: '🏆 승리 조건',
    fail_condition: '💀 실패 조건',
    system_rule: '⚙️ 시스템 규칙',
    hidden_trick: '🔐 숨겨진 트릭',
  };
  return labels[ruleType] || ruleType;
}

// 노드 타입별 색상
function getNodeColor(type: string): string {
  const colors: Record<string, string> = {
    Scenario: '#ff6b6b',
    Character: '#4ecdc4',
    Location: '#45b7d1',
    Event: '#f7b731',
    Rule: '#5f27cd',
    Item: '#00d2d3',
    Skill: '#ff9ff3',
    Trick: '#feca57',
    SystemMessage: '#48dbfb',
  };
  return colors[type] || '#95a5a6';
}

// 노드 타입별 모양
function getNodeShape(type: string): string {
  const shapes: Record<string, string> = {
    Scenario: 'box',
    Character: 'ellipse',
    Location: 'diamond',
    Event: 'star',
    Rule: 'hexagon',
    Item: 'triangle',
    Skill: 'dot',
    Trick: 'square',
    SystemMessage: 'box',
  };
  return shapes[type] || 'dot';
}
