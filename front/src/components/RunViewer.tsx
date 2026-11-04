import { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import './RunViewer.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ===== 타입 =====
interface EntityResult {
  id: string;
  document: string;
  score?: number;
  metadata: {
    title: string;
    entity_type: string;
    tags?: string[];
    [key: string]: any;
  };
  relations?: Array<{
    title: string;
    type: string;
    label?: string;
  }>;
}

interface QueryResponse {
  query: string;
  query_type: string;
  response: string;
  data: {
    entities?: Array<{
      id: string;
      title: string;
      entity_type: string;
      score: number;
      relations: Array<{ title: string; type: string }>;
    }>;
  } | null;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  entities?: Array<{ id: string; title: string; entity_type: string }>;
}

interface GraphNode {
  id: string;
  title: string;
  label: string;
}

interface GraphEdge {
  source: string;
  target: string;
  relation_type: string;
}

type ViewTab = 'chat' | 'entities' | 'graph';
type EntityTypeFilter = '' | 'concept' | 'character' | 'event' | 'world_setting';

const TYPE_LABELS: Record<string, string> = {
  concept: '개념',
  character: '인물',
  event: '사건',
  world_setting: '세계관',
};

const TYPE_COLORS: Record<string, string> = {
  RunConcept: '#7c6fff',
  RunCharacter: '#ff6b8a',
  RunEvent: '#4ecdc4',
  RunWorldSetting: '#ffd93d',
  concept: '#7c6fff',
  character: '#ff6b8a',
  event: '#4ecdc4',
  world_setting: '#ffd93d',
};

export default function RunViewer({ onBack }: { onBack: () => void }) {
  const [viewTab, setViewTab] = useState<ViewTab>('chat');
  const [vectorCount, setVectorCount] = useState(0);

  // 질의 상태
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 엔티티 상태
  const [entities, setEntities] = useState<EntityResult[]>([]);
  const [entityFilter, setEntityFilter] = useState<EntityTypeFilter>('');
  const [entitySearch, setEntitySearch] = useState('');
  const [selectedEntity, setSelectedEntity] = useState<EntityResult | null>(null);

  // 그래프 상태
  const graphContainerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  // === 초기 로드 ===
  useEffect(() => {
    loadStats();
    loadEntities();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (viewTab === 'graph') loadGraph();
  }, [viewTab]);

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/run/stats`);
      const data = await res.json();
      setVectorCount(data.pinecone?.total_count || 0);
    } catch { /* ignore */ }
  };

  // === 질의 ===
  const handleQuery = async () => {
    const q = query.trim();
    if (!q || isLoading) return;

    setQuery('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/run/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      const data: QueryResponse = await res.json();

      const entities = data.data?.entities?.map(e => ({
        id: e.id,
        title: e.title,
        entity_type: e.entity_type,
      })) || [];

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        entities,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '오류가 발생했습니다. 서버 연결을 확인해주세요.',
      }]);
    }
    setIsLoading(false);
  };

  // === 엔티티 검색 ===
  const loadEntities = async (searchQuery?: string, typeFilter?: string) => {
    try {
      const q = searchQuery || '런 세계관';
      const body: any = { query: q, limit: 30 };
      if (typeFilter) body.entity_types = [typeFilter];

      const res = await fetch(`${API_URL}/api/run/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      setEntities(data.results || []);
    } catch {
      setEntities([]);
    }
  };

  const handleEntitySearch = () => {
    loadEntities(entitySearch || undefined, entityFilter || undefined);
  };

  useEffect(() => {
    if (viewTab === 'entities') {
      loadEntities(entitySearch || undefined, entityFilter || undefined);
    }
  }, [entityFilter]);

  const loadEntityDetail = async (entityId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/run/entities/${encodeURIComponent(entityId)}`);
      const data = await res.json();
      if (!data.error) setSelectedEntity(data);
    } catch { /* ignore */ }
  };

  // === 그래프 ===
  const loadGraph = async () => {
    try {
      const res = await fetch(`${API_URL}/api/run/graph?limit=100`);
      const data = await res.json();
      renderGraph(data);
    } catch { /* ignore */ }
  };

  const renderGraph = (data: { nodes: GraphNode[]; edges: GraphEdge[] }) => {
    if (!graphContainerRef.current || !data.nodes?.length) return;

    const nodes = data.nodes.map((n) => ({
      id: n.id,
      label: n.title,
      color: TYPE_COLORS[n.label] || '#666',
      font: { color: '#ccc', size: 12 },
      shape: n.label === 'RunCharacter' ? 'dot' :
             n.label === 'RunEvent' ? 'diamond' :
             n.label === 'RunConcept' ? 'triangle' : 'square',
      size: n.label === 'RunCharacter' ? 18 : 14,
    }));

    const edges = data.edges.map((e) => ({
      from: e.source,
      to: e.target,
      label: e.relation_type,
      color: { color: '#333', highlight: '#666' },
      font: { color: '#555', size: 9 },
      arrows: 'to',
    }));

    if (networkRef.current) networkRef.current.destroy();

    networkRef.current = new Network(
      graphContainerRef.current,
      { nodes, edges },
      {
        physics: {
          solver: 'barnesHut',
          barnesHut: { gravitationalConstant: -3000, springLength: 150 },
          stabilization: { iterations: 100 },
        },
        interaction: { hover: true, zoomView: true },
        layout: { improvedLayout: true },
      }
    );
  };

  // === 렌더링 ===
  return (
    <div className="run-viewer">
      {/* 헤더 */}
      <div className="header">
        <button className="back-btn" onClick={onBack}>← 뒤로</button>
        <h1>런 세계관</h1>
        <span className="stats-badge">{vectorCount} entities</span>
      </div>

      {/* 탭 */}
      <div className="tabs">
        <button className={viewTab === 'chat' ? 'active' : ''} onClick={() => setViewTab('chat')}>
          질의
        </button>
        <button className={viewTab === 'entities' ? 'active' : ''} onClick={() => setViewTab('entities')}>
          엔티티
        </button>
        <button className={viewTab === 'graph' ? 'active' : ''} onClick={() => setViewTab('graph')}>
          그래프
        </button>
      </div>

      {/* 메인 */}
      <div className="main">
        {/* 질의 탭 */}
        {viewTab === 'chat' && (
          <div className="chat-panel">
            <div className="messages">
              {messages.length === 0 && (
                <div className="empty-state">
                  런 세계관에 대해 질문해보세요.<br />
                  예: "인지적 고리가 뭐야?", "세르게이와 런의 관계는?"
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <div>{msg.content}</div>
                  {msg.entities && msg.entities.length > 0 && (
                    <div className="entity-chips">
                      {msg.entities.map((e, j) => (
                        <span
                          key={j}
                          className={`entity-chip ${e.entity_type}`}
                          onClick={() => loadEntityDetail(e.id)}
                        >
                          {TYPE_LABELS[e.entity_type] || e.entity_type}: {e.title}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="message assistant">
                  <div>생각 중...</div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="input-area">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
                placeholder="세계관에 대해 질문하세요..."
                disabled={isLoading}
              />
              <button onClick={handleQuery} disabled={isLoading || !query.trim()}>
                전송
              </button>
            </div>
          </div>
        )}

        {/* 엔티티 탭 */}
        {viewTab === 'entities' && (
          <div className="entities-panel">
            <div className="filter-bar">
              {(['', 'concept', 'character', 'event', 'world_setting'] as EntityTypeFilter[]).map(type => (
                <button
                  key={type}
                  className={`type-btn ${entityFilter === type ? 'active' : ''}`}
                  onClick={() => setEntityFilter(type)}
                >
                  {type ? TYPE_LABELS[type] : '전체'}
                </button>
              ))}
              <input
                className="search-input"
                value={entitySearch}
                onChange={(e) => setEntitySearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleEntitySearch()}
                placeholder="검색어 입력..."
              />
            </div>
            <div className="entity-list">
              {entities.length === 0 && <div className="empty-state">검색 결과가 없습니다.</div>}
              {entities.map((entity) => {
                const type = entity.metadata.entity_type;
                const tags = entity.metadata.tags || [];
                return (
                  <div
                    key={entity.id}
                    className="entity-card"
                    onClick={() => loadEntityDetail(entity.id)}
                  >
                    <div className="card-header">
                      <span className={`type-badge ${type}`}>{TYPE_LABELS[type] || type}</span>
                      <span className="card-title">{entity.metadata.title}</span>
                    </div>
                    <div className="card-excerpt">{entity.document?.slice(0, 120)}</div>
                    {tags.length > 0 && (
                      <div className="card-tags">
                        {tags.slice(0, 4).map((tag, i) => (
                          <span key={i} className="tag">{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 그래프 탭 */}
        {viewTab === 'graph' && (
          <div className="graph-panel">
            <div className="graph-container" ref={graphContainerRef} />
            <div className="graph-legend">
              <div className="legend-item">
                <span className="legend-dot" style={{ background: '#ff6b8a' }} />인물
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ background: '#7c6fff' }} />개념
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ background: '#4ecdc4' }} />사건
              </div>
              <div className="legend-item">
                <span className="legend-dot" style={{ background: '#ffd93d' }} />세계관
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 엔티티 상세 모달 */}
      {selectedEntity && (
        <div className="entity-detail-overlay" onClick={() => setSelectedEntity(null)}>
          <div className="entity-detail" onClick={(e) => e.stopPropagation()}>
            <div className="detail-header">
              <div>
                <span className={`type-badge ${selectedEntity.metadata.entity_type}`}>
                  {TYPE_LABELS[selectedEntity.metadata.entity_type] || selectedEntity.metadata.entity_type}
                </span>
                <h2>{selectedEntity.metadata.title}</h2>
              </div>
              <button className="close-btn" onClick={() => setSelectedEntity(null)}>x</button>
            </div>
            <div className="detail-content">{selectedEntity.document}</div>
            {selectedEntity.relations && selectedEntity.relations.length > 0 && (
              <div className="relations-section">
                <h3>관계</h3>
                {selectedEntity.relations.map((rel, i) => (
                  <div key={i} className="relation-item">
                    {rel.type} → {rel.title}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
