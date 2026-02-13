import { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import './MyeolsalViewer.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ===== 타입 정의 =====
interface BeastMetadata {
  title: string;
  grade: string;
  species: string;
  danger_class: string;
  layer: string;
  confidence: number;
  tags: string[];
  weaknesses: string[];
  resistances: string[];
  appearance_scenarios: string[];
}

interface BeastResult {
  id: string;
  document: string;
  metadata: BeastMetadata;
  distance?: number;
}

interface QueryResponse {
  query: string;
  response: string;
  query_type: string | null;
  data: {
    beasts?: BeastResult[];
    beast?: any;
  } | null;
}

interface GraphNode {
  id: string;
  label: string;
  grade: string;
  species: string;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface Stats {
  pinecone: {
    total_count: number;
    grade_distribution: Record<string, number>;
    species_distribution: Record<string, number>;
    scenario_distribution: Record<string, number>;
  };
  rules: {
    grades: number;
    species: number;
    elements: number;
  };
}

type ViewTab = 'chat' | 'beasts' | 'graph';

export default function MyeolsalViewer({ onBack }: { onBack: () => void }) {
  // === 상태 ===
  const [viewTab, setViewTab] = useState<ViewTab>('chat');
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [beasts, setBeasts] = useState<BeastResult[]>([]);
  const [selectedBeast, setSelectedBeast] = useState<BeastResult | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [searchFilter, setSearchFilter] = useState({ grade: '', species: '' });
  const [beastListTotal, setBeastListTotal] = useState(0);
  const [beastListHasMore, setBeastListHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // === 초기 로드 ===
  useEffect(() => {
    loadStats();
    loadBeasts('');
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // === 그래프 렌더링 ===
  useEffect(() => {
    if (viewTab !== 'graph' || !containerRef.current || !graphData) return;

    const nodes = graphData.nodes.map((node) => ({
      id: node.id,
      label: `${node.label}\n(${node.grade})`,
      color: getGradeColor(node.grade),
      shape: getSpeciesShape(node.species),
      font: { size: 12, color: '#fff' },
    }));

    const edges = graphData.edges.map((edge, i) => ({
      id: `edge_${i}`,
      from: edge.source,
      to: edge.target,
      label: edge.type,
      arrows: 'to',
      font: { size: 10, align: 'middle' as const },
    }));

    if (networkRef.current) {
      networkRef.current.destroy();
    }

    const network = new Network(
      containerRef.current,
      { nodes, edges },
      {
        nodes: {
          borderWidth: 2,
          font: { color: '#ffffff', size: 12 },
        },
        edges: {
          color: { color: '#666', highlight: '#ff9500' },
          smooth: { enabled: true, type: 'cubicBezier', roundness: 0.4 },
        },
        physics: {
          enabled: true,
          stabilization: { iterations: 150 },
          barnesHut: {
            gravitationalConstant: -5000,
            springConstant: 0.04,
            springLength: 120,
          },
        },
        interaction: { hover: true },
      }
    );

    network.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const beast = beasts.find((b) => b.id === nodeId);
        if (beast) setSelectedBeast(beast);
      }
    });

    networkRef.current = network;

    return () => {
      networkRef.current?.destroy();
      networkRef.current = null;
    };
  }, [viewTab, graphData]);

  // === API 호출 ===
  const loadStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/myeolsal/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  };

  const loadBeasts = async (_searchQuery?: string) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({ offset: '0', limit: '50' });
      if (searchFilter.grade) params.append('grade', searchFilter.grade);
      if (searchFilter.species) params.append('species', searchFilter.species);

      const res = await fetch(`${API_URL}/api/myeolsal/beasts/list?${params}`);
      const data = await res.json();
      setBeasts(data.results || []);
      setBeastListTotal(data.total || 0);
      setBeastListHasMore(data.has_more || false);
    } catch (err) {
      console.error('Failed to load beasts:', err);
    }
    setIsLoading(false);
  };

  const loadMoreBeasts = async () => {
    setIsLoadingMore(true);
    try {
      const nextOffset = beasts.length;
      const params = new URLSearchParams({ offset: String(nextOffset), limit: '50' });
      if (searchFilter.grade) params.append('grade', searchFilter.grade);
      if (searchFilter.species) params.append('species', searchFilter.species);

      const res = await fetch(`${API_URL}/api/myeolsal/beasts/list?${params}`);
      const data = await res.json();
      setBeasts((prev) => [...prev, ...(data.results || [])]);
      setBeastListTotal(data.total || 0);
      setBeastListHasMore(data.has_more || false);
    } catch (err) {
      console.error('Failed to load more beasts:', err);
    }
    setIsLoadingMore(false);
  };

  const loadGraph = async () => {
    try {
      const res = await fetch(`${API_URL}/api/myeolsal/graph?limit=100`);
      const data = await res.json();
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load graph:', err);
    }
  };

  const sendQuery = async () => {
    if (!query.trim() || isLoading) return;

    const userMessage = query.trim();
    setQuery('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/myeolsal/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage }),
      });
      const data: QueryResponse = await res.json();

      setMessages((prev) => [...prev, { role: 'assistant', content: data.response }]);

      // 검색된 괴수가 있으면 업데이트
      if (data.data?.beasts) {
        setBeasts(data.data.beasts);
      }
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'system', content: '오류가 발생했습니다.' }]);
    }
    setIsLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendQuery();
    }
  };

  const initializeData = async () => {
    setIsLoading(true);
    try {
      await fetch(`${API_URL}/api/myeolsal/seed`, { method: 'POST' });
      await loadStats();
      await loadBeasts('');
      setMessages((prev) => [...prev, { role: 'system', content: '시드 데이터가 로드되었습니다.' }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'system', content: '초기화 실패' }]);
    }
    setIsLoading(false);
  };

  // === 탭 전환 ===
  const handleTabChange = (tab: ViewTab) => {
    setViewTab(tab);
    if (tab === 'graph' && !graphData) {
      loadGraph();
    }
  };

  return (
    <div className="myeolsal-viewer">
      {/* 헤더 */}
      <header className="myeolsal-header">
        <button className="back-btn" onClick={onBack}>← 돌아가기</button>
        <h1>tls123의 괴수 백과 [신간]</h1>
        <div className="header-stats">
          {stats && (
            <>
              <span className="stat-badge">괴수 {stats.pinecone.total_count}종</span>
              <span className="stat-badge">등급 {stats.rules.grades}개</span>
            </>
          )}
        </div>
      </header>

      {/* 탭 네비게이션 */}
      <nav className="myeolsal-tabs">
        <button className={viewTab === 'chat' ? 'active' : ''} onClick={() => handleTabChange('chat')}>
          💬 대화 검색
        </button>
        <button className={viewTab === 'beasts' ? 'active' : ''} onClick={() => handleTabChange('beasts')}>
          📖 괴수 목록
        </button>
        <button className={viewTab === 'graph' ? 'active' : ''} onClick={() => handleTabChange('graph')}>
          🔗 관계 그래프
        </button>
      </nav>

      {/* 메인 콘텐츠 */}
      <main className="myeolsal-content">
        {/* === 대화 검색 탭 === */}
        {viewTab === 'chat' && (
          <div className="chat-view">
            <div className="chat-messages">
              {messages.length === 0 && (
                <div className="welcome-message">
                  <h2>tls123의 괴수 백과</h2>
                  <p>멸살법 저자 tls123이 집필한 괴수 생존 가이드입니다.</p>
                  <div className="example-queries">
                    <button onClick={() => setQuery('7급 해수종 어떻게 상대해?')}>
                      "7급 해수종 어떻게 상대해?"
                    </button>
                    <button onClick={() => setQuery('화염에 약한 괴수 알려줘')}>
                      "화염에 약한 괴수 알려줘"
                    </button>
                    <button onClick={() => setQuery('스틸울프 생존법')}>
                      "스틸울프 생존법"
                    </button>
                  </div>
                  {stats?.pinecone.total_count === 0 && (
                    <button className="init-btn" onClick={initializeData} disabled={isLoading}>
                      {isLoading ? '로딩 중...' : '📥 시드 데이터 로드'}
                    </button>
                  )}
                </div>
              )}
              {messages.map((msg, i) => (
                <div key={i} className={`chat-message ${msg.role}`}>
                  <div className="message-content">{msg.content}</div>
                </div>
              ))}
              {isLoading && (
                <div className="chat-message assistant loading">
                  <div className="message-content">검색 중...</div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="chat-input">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="괴수에 대해 물어보세요..."
                disabled={isLoading}
              />
              <button onClick={sendQuery} disabled={isLoading || !query.trim()}>
                검색
              </button>
            </div>
          </div>
        )}

        {/* === 괴수 목록 탭 === */}
        {viewTab === 'beasts' && (
          <div className="beasts-view">
            {/* 필터 */}
            <div className="beasts-filter">
              <select
                value={searchFilter.grade}
                onChange={(e) => {
                  setSearchFilter((prev) => ({ ...prev, grade: e.target.value }));
                }}
              >
                <option value="">전체 등급</option>
                {['9급', '8급', '7급', '6급', '5급', '4급', '3급', '2급', '1급', '특급', '히든', '권외', '???'].map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
              <select
                value={searchFilter.species}
                onChange={(e) => {
                  setSearchFilter((prev) => ({ ...prev, species: e.target.value }));
                }}
              >
                <option value="">전체 종</option>
                {(stats?.pinecone.species_distribution
                  ? Object.keys(stats.pinecone.species_distribution).sort()
                  : ['괴수종', '악마종', '해수종', '충왕종', '거신', '재앙']
                ).map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <button onClick={() => loadBeasts('')}>적용</button>
            </div>

            {/* 통계 */}
            {stats && (
              <div className="beasts-stats">
                <div className="stats-section">
                  <h4>등급 분포</h4>
                  <div className="stats-bars">
                    {Object.entries(stats.pinecone.grade_distribution).map(([grade, count]) => (
                      <div key={grade} className="stat-bar">
                        <span className="stat-label">{grade}</span>
                        <div className="stat-fill" style={{ width: `${(count / stats.pinecone.total_count) * 100}%` }} />
                        <span className="stat-count">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 괴수 그리드 */}
            <div className="beasts-grid">
              {beasts.map((beast) => (
                <div
                  key={beast.id}
                  className={`beast-card ${beast.metadata.danger_class}`}
                  onClick={() => setSelectedBeast(beast)}
                >
                  <div className="beast-header">
                    <span className={`grade-badge ${beast.metadata.grade.replace('급', '')}`}>
                      {beast.metadata.grade}
                    </span>
                    <span className="species-badge">{beast.metadata.species}</span>
                  </div>
                  <h3 className="beast-title">{beast.metadata.title}</h3>
                  <p className="beast-preview">{beast.document?.slice(0, 80)}...</p>
                  <div className="beast-tags">
                    {beast.metadata.weaknesses?.slice(0, 2).map((w, i) => (
                      <span key={i} className="tag weakness">⚡ {w}</span>
                    ))}
                  </div>
                </div>
              ))}
              {beasts.length === 0 && !isLoading && (
                <div className="empty-state">
                  <p>괴수를 찾을 수 없습니다.</p>
                  <button onClick={initializeData}>시드 데이터 로드</button>
                </div>
              )}
            </div>

            {/* 페이지네이션 */}
            {beasts.length > 0 && (
              <div className="beasts-pagination">
                <span className="beasts-count">{beasts.length} / {beastListTotal}종</span>
                {beastListHasMore && (
                  <button className="load-more-btn" onClick={loadMoreBeasts} disabled={isLoadingMore}>
                    {isLoadingMore ? '불러오는 중...' : '더 보기'}
                  </button>
                )}
              </div>
            )}
          </div>
        )}

        {/* === 관계 그래프 탭 === */}
        {viewTab === 'graph' && (
          <div className="graph-view">
            <div className="coming-soon">
              <p>추후 업데이트 예정</p>
            </div>
          </div>
        )}
      </main>

      {/* === 괴수 상세 모달 === */}
      {selectedBeast && (
        <div className="beast-modal-overlay" onClick={() => setSelectedBeast(null)}>
          <div className="beast-modal" onClick={(e) => e.stopPropagation()}>
            <button className="close-btn" onClick={() => setSelectedBeast(null)}>✕</button>

            <div className="modal-header">
              <span className={`grade-badge large ${selectedBeast.metadata.grade.replace('급', '')}`}>
                {selectedBeast.metadata.grade}
              </span>
              <h2>{selectedBeast.metadata.title}</h2>
              <span className="species-badge">{selectedBeast.metadata.species}</span>
              <span className={`danger-badge ${selectedBeast.metadata.danger_class}`}>
                {selectedBeast.metadata.danger_class}
              </span>
            </div>

            <div className="modal-body">
              <section>
                <h4>설명</h4>
                <p>{selectedBeast.document}</p>
              </section>

              <section className="stats-section">
                <h4>약점 & 저항</h4>
                <div className="element-tags">
                  <div className="weaknesses">
                    <span className="label">약점:</span>
                    {selectedBeast.metadata.weaknesses?.map((w, i) => (
                      <span key={i} className="tag weakness">{w}</span>
                    ))}
                  </div>
                  <div className="resistances">
                    <span className="label">저항:</span>
                    {selectedBeast.metadata.resistances?.map((r, i) => (
                      <span key={i} className="tag resistance">{r}</span>
                    ))}
                  </div>
                </div>
              </section>

              {selectedBeast.metadata.appearance_scenarios?.length > 0 && (
                <section>
                  <h4>등장 시나리오</h4>
                  <div className="scenario-tags">
                    {selectedBeast.metadata.appearance_scenarios.map((s, i) => (
                      <span key={i} className="tag scenario">{formatScenarioName(s)}</span>
                    ))}
                  </div>
                </section>
              )}

              <section>
                <h4>데이터 정보</h4>
                <div className="meta-info">
                  <span>계층: {selectedBeast.metadata.layer}</span>
                  <span>신뢰도: {Math.round(selectedBeast.metadata.confidence * 100)}%</span>
                </div>
              </section>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// === 유틸리티 함수 ===
function getGradeColor(grade: string): string {
  const colors: Record<string, string> = {
    '9급': '#78909c',
    '8급': '#8bc34a',
    '7급': '#4caf50',
    '6급': '#2196f3',
    '5급': '#9c27b0',
    '4급': '#e91e63',
    '3급': '#f44336',
    '2급': '#ff5722',
    '1급': '#ff9800',
    '특급': '#ffd700',
  };
  return colors[grade] || '#666';
}

function getSpeciesShape(species: string): string {
  const shapes: Record<string, string> = {
    '괴수종': 'dot',
    '악마종': 'diamond',
    '해수종': 'triangle',
    '충왕종': 'star',
    '거신': 'square',
    '재앙': 'hexagon',
  };
  return shapes[species] || 'dot';
}

function formatScenarioName(scenario: string): string {
  // scenario_main_001 -> 메인 #1
  // scenario_side_005 -> 사이드 #5
  const match = scenario.match(/scenario_(main|side)_(\d+)/);
  if (match) {
    const type = match[1] === 'main' ? '메인' : '사이드';
    const num = parseInt(match[2], 10);
    return `${type} #${num}`;
  }
  return scenario;
}
