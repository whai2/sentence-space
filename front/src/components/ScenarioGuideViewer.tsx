import { useEffect, useRef, useState } from 'react';
import { Network } from 'vis-network';
import './ScenarioGuideViewer.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ===== 타입 정의 =====
interface PlayerPath {
  path: string;
  difficulty: string;
  moral_cost: string;
  narrative_tone: string;
}

interface ScenarioRule {
  type: string;
  objective: string;
  clear_condition: string;
  failure_condition: string;
  failure_penalty: string;
  time_limit: string | null;
  participants: string;
  constraints: string[];
}

interface Interpretation {
  surface_reading: string;
  hidden_solution: string;
  protagonist_advantage: string;
  player_possible_paths: PlayerPath[];
}

interface Stage {
  name: string;
  description: string;
  terrain_features: string[];
  atmosphere: string;
}

interface Narrative {
  arc_position: string;
  tone: string;
  key_events: string[];
  plot_hooks: string[];
  previous_scenario_summary: string;
}

interface LinkedBeast {
  beast_id: string;
  title: string;
  grade: string;
  species: string;
  appearance_type: string;
}

interface ScenarioPackage {
  id: string;
  name: string;
  title: string;
  scenario_rule: ScenarioRule;
  interpretation: Interpretation;
  stage: Stage;
  monster_refs: string[];
  character_refs: string[];
  narrative: Narrative;
  linked_beasts?: LinkedBeast[];
}

interface ScenarioStats {
  total: number;
  type_distribution: Record<string, number>;
}

interface GraphNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
}

interface GraphEdge {
  from: string;
  to: string;
  type: string;
  properties: Record<string, any>;
}

type ViewTab = 'scenarios' | 'graph';

export default function ScenarioGuideViewer({ onBack }: { onBack: () => void }) {
  const [viewTab, setViewTab] = useState<ViewTab>('scenarios');
  const [scenarios, setScenarios] = useState<ScenarioPackage[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioPackage | null>(null);
  const [stats, setStats] = useState<ScenarioStats | null>(null);
  const [typeFilter, setTypeFilter] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // 해석 레이어 토글 상태
  const [openInterp, setOpenInterp] = useState<Record<string, boolean>>({});

  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  // === 초기 로드 ===
  useEffect(() => {
    loadStats();
    loadScenarios();
  }, []);

  const loadStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/scenario/stats`);
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Stats load failed:', err);
    }
  };

  const loadScenarios = async (type?: string) => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({ offset: '0', limit: '100' });
      if (type) params.set('type', type);

      const res = await fetch(`${API_URL}/api/scenario/list?${params}`);
      const data = await res.json();
      setScenarios(data.results || []);
    } catch (err) {
      console.error('Scenarios load failed:', err);
    }
    setIsLoading(false);
  };

  const loadScenarioDetail = async (scenarioId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/scenario/${scenarioId}`);
      const data = await res.json();
      setSelectedScenario(data);
      setOpenInterp({});
    } catch (err) {
      console.error('Scenario detail load failed:', err);
    }
  };

  const initializeData = async () => {
    setIsLoading(true);
    try {
      await fetch(`${API_URL}/api/scenario/seed?force=true`, { method: 'POST' });
      await loadStats();
      await loadScenarios();
    } catch (err) {
      console.error('Seed failed:', err);
    }
    setIsLoading(false);
  };

  const handleFilterChange = (type: string) => {
    setTypeFilter(type);
    loadScenarios(type || undefined);
  };

  const toggleInterp = (key: string) => {
    setOpenInterp(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // === 그래프 로드 ===
  useEffect(() => {
    if (viewTab !== 'graph' || !containerRef.current) return;

    const loadGraph = async () => {
      try {
        const res = await fetch(`${API_URL}/api/scenario/graph?limit=200`);
        const data = await res.json();

        const nodes = (data.nodes || []).map((n: GraphNode) => ({
          id: n.id,
          label: n.label,
          color: n.type === 'Scenario' ? '#f6ad55' : '#63b3ed',
          shape: n.type === 'Scenario' ? 'box' : 'dot',
          font: { color: '#e0e0e0', size: 12 },
        }));

        const edges = (data.edges || []).map((e: GraphEdge, i: number) => ({
          id: `edge-${i}`,
          from: e.from,
          to: e.to,
          label: e.type,
          color: { color: '#4a3f6f', highlight: '#d6bcfa' },
          font: { color: '#718096', size: 10 },
        }));

        if (networkRef.current) {
          networkRef.current.destroy();
        }

        networkRef.current = new Network(
          containerRef.current!,
          { nodes, edges },
          {
            physics: {
              solver: 'barnesHut',
              barnesHut: { gravitationalConstant: -3000, springLength: 150 },
            },
            interaction: { hover: true, tooltipDelay: 200 },
          }
        );
      } catch (err) {
        console.error('Graph load failed:', err);
      }
    };

    loadGraph();

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [viewTab]);

  // === 유틸 ===
  const getMoralCostClass = (cost: string) => {
    if (cost.includes('높음') || cost.includes('매우')) return 'moral-cost-high';
    if (cost.includes('중간')) return 'moral-cost-medium';
    if (cost.includes('낮음')) return 'moral-cost-low';
    return 'moral-cost-none';
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = { main: '메인', sub: '서브', hidden: '히든' };
    return labels[type] || type;
  };

  return (
    <div className="scenario-viewer">
      {/* 헤더 */}
      <header className="scenario-header">
        <button className="back-btn" onClick={onBack}>← 돌아가기</button>
        <h1>시나리오 설명집</h1>
        {stats && (
          <div className="header-stats">
            <span className="stat-badge">시나리오 {stats.total}개</span>
          </div>
        )}
      </header>

      {/* 탭 */}
      <nav className="scenario-tabs">
        <button className={viewTab === 'scenarios' ? 'active' : ''} onClick={() => setViewTab('scenarios')}>
          시나리오 목록
        </button>
        <button className={viewTab === 'graph' ? 'active' : ''} onClick={() => setViewTab('graph')}>
          관계 그래프
        </button>
      </nav>

      {/* 콘텐츠 */}
      <main className="scenario-content">
        {/* === 시나리오 목록 탭 === */}
        {viewTab === 'scenarios' && (
          <div className="scenarios-view">
            {/* 필터 */}
            <div className="scenarios-filter">
              <select value={typeFilter} onChange={(e) => handleFilterChange(e.target.value)}>
                <option value="">전체 유형</option>
                <option value="main">메인</option>
                <option value="sub">서브</option>
                <option value="hidden">히든</option>
              </select>
            </div>

            {/* 시나리오 그리드 */}
            <div className="scenarios-grid">
              {scenarios.map((sc) => (
                <div
                  key={sc.id}
                  className={`scenario-card ${sc.scenario_rule.type}`}
                  onClick={() => loadScenarioDetail(sc.id)}
                >
                  <div className="scenario-card-header">
                    <span className="scenario-id-badge">{sc.id}</span>
                    <span className={`scenario-type-badge ${sc.scenario_rule.type}`}>
                      {getTypeLabel(sc.scenario_rule.type)}
                    </span>
                  </div>
                  <p className="scenario-card-name">{sc.name}</p>
                  <h3 className="scenario-card-title">{sc.title}</h3>
                  <div className="scenario-card-objective">
                    {sc.scenario_rule.objective}
                  </div>
                  <div className="scenario-card-footer">
                    <span className="tag stage">{sc.stage.name}</span>
                    {sc.scenario_rule.time_limit && (
                      <span className="tag time">{sc.scenario_rule.time_limit}</span>
                    )}
                    <span className="tag penalty">{sc.scenario_rule.failure_penalty}</span>
                  </div>
                </div>
              ))}
              {scenarios.length === 0 && !isLoading && (
                <div className="empty-state">
                  <p>시나리오가 없습니다.</p>
                  <button onClick={initializeData}>시드 데이터 로드</button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* === 관계 그래프 탭 === */}
        {viewTab === 'graph' && (
          <div className="graph-view">
            <div className="graph-legend">
              <span><span className="dot scenario" /> 시나리오</span>
              <span><span className="dot beast" /> 괴수</span>
            </div>
            <div ref={containerRef} className="graph-container" />
          </div>
        )}
      </main>

      {/* === 시나리오 상세 모달 === */}
      {selectedScenario && (
        <div className="scenario-modal-overlay" onClick={() => setSelectedScenario(null)}>
          <div className="scenario-modal" onClick={(e) => e.stopPropagation()}>
            <button className="close-btn" onClick={() => setSelectedScenario(null)}>✕</button>

            {/* 헤더 */}
            <div className="scenario-modal-header">
              <div className="header-badges">
                <span className="scenario-id-badge">{selectedScenario.id}</span>
                <span className={`scenario-type-badge ${selectedScenario.scenario_rule.type}`}>
                  {getTypeLabel(selectedScenario.scenario_rule.type)}
                </span>
              </div>
              <h2>{selectedScenario.title}</h2>
              <span className="subtitle">{selectedScenario.name}</span>
            </div>

            {/* 바디 */}
            <div className="scenario-modal-body">
              {/* 시나리오 규칙 */}
              <section>
                <h4>시나리오 규칙</h4>
                <div className="rule-grid">
                  <div className="rule-item full-width">
                    <div className="rule-label">목표</div>
                    <div className="rule-value">{selectedScenario.scenario_rule.objective}</div>
                  </div>
                  <div className="rule-item">
                    <div className="rule-label">클리어 조건</div>
                    <div className="rule-value">{selectedScenario.scenario_rule.clear_condition}</div>
                  </div>
                  <div className="rule-item">
                    <div className="rule-label">실패 조건</div>
                    <div className="rule-value">{selectedScenario.scenario_rule.failure_condition}</div>
                  </div>
                  <div className="rule-item">
                    <div className="rule-label">실패 시</div>
                    <div className="rule-value">{selectedScenario.scenario_rule.failure_penalty}</div>
                  </div>
                  {selectedScenario.scenario_rule.time_limit && (
                    <div className="rule-item">
                      <div className="rule-label">시간 제한</div>
                      <div className="rule-value">{selectedScenario.scenario_rule.time_limit}</div>
                    </div>
                  )}
                  <div className="rule-item full-width">
                    <div className="rule-label">참가자</div>
                    <div className="rule-value">{selectedScenario.scenario_rule.participants}</div>
                  </div>
                  {selectedScenario.scenario_rule.constraints.length > 0 && (
                    <div className="rule-item full-width">
                      <div className="rule-label">제약 조건</div>
                      <ul className="constraints-list">
                        {selectedScenario.scenario_rule.constraints.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>

              {/* 해석 레이어 */}
              <section>
                <h4>해석 레이어</h4>
                <div className="interpretation-block">
                  <div className="interp-item surface">
                    <button
                      className={`interp-toggle ${openInterp['surface'] ? 'open' : ''}`}
                      onClick={() => toggleInterp('surface')}
                    >
                      <span>표면적 해석 — 대부분의 탑승자가 이해하는 방식</span>
                      <span className="arrow">▶</span>
                    </button>
                    {openInterp['surface'] && (
                      <div className="interp-content">
                        {selectedScenario.interpretation.surface_reading}
                      </div>
                    )}
                  </div>

                  <div className="interp-item hidden-sol">
                    <button
                      className={`interp-toggle ${openInterp['hidden'] ? 'open' : ''}`}
                      onClick={() => toggleInterp('hidden')}
                    >
                      <span>숨겨진 해법 — 실제 최적해</span>
                      <span className="arrow">▶</span>
                    </button>
                    {openInterp['hidden'] && (
                      <div className="interp-content">
                        {selectedScenario.interpretation.hidden_solution}
                      </div>
                    )}
                  </div>

                  <div className="interp-item advantage">
                    <button
                      className={`interp-toggle ${openInterp['advantage'] ? 'open' : ''}`}
                      onClick={() => toggleInterp('advantage')}
                    >
                      <span>주인공의 이점 — 김독자의 선지자적 지식</span>
                      <span className="arrow">▶</span>
                    </button>
                    {openInterp['advantage'] && (
                      <div className="interp-content">
                        {selectedScenario.interpretation.protagonist_advantage}
                      </div>
                    )}
                  </div>
                </div>
              </section>

              {/* 플레이어 가능 경로 */}
              {selectedScenario.interpretation.player_possible_paths.length > 0 && (
                <section>
                  <h4>플레이어 가능 경로</h4>
                  <table className="paths-table">
                    <thead>
                      <tr>
                        <th>경로</th>
                        <th>난이도</th>
                        <th>도덕적 비용</th>
                        <th>서사 톤</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedScenario.interpretation.player_possible_paths.map((p, i) => (
                        <tr key={i}>
                          <td>{p.path}</td>
                          <td>{p.difficulty}</td>
                          <td className={getMoralCostClass(p.moral_cost)}>{p.moral_cost}</td>
                          <td>{p.narrative_tone}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              )}

              {/* 무대 정보 */}
              <section>
                <h4>무대</h4>
                <div className="stage-block">
                  <div className="stage-name">{selectedScenario.stage.name}</div>
                  <div className="stage-desc">{selectedScenario.stage.description}</div>
                  {selectedScenario.stage.terrain_features.length > 0 && (
                    <ul className="terrain-list">
                      {selectedScenario.stage.terrain_features.map((t, i) => (
                        <li key={i}>{t}</li>
                      ))}
                    </ul>
                  )}
                  {selectedScenario.stage.atmosphere && (
                    <div className="atmosphere-text">{selectedScenario.stage.atmosphere}</div>
                  )}
                </div>
              </section>

              {/* 서사 정보 */}
              <section>
                <h4>서사</h4>
                <div className="narrative-block">
                  <div className="narrative-meta">
                    <span className="meta-tag">
                      <span className="meta-label">아크:</span>
                      {selectedScenario.narrative.arc_position}
                    </span>
                    <span className="meta-tag">
                      <span className="meta-label">톤:</span>
                      {selectedScenario.narrative.tone}
                    </span>
                  </div>

                  {selectedScenario.narrative.key_events.length > 0 && (
                    <div>
                      <h4>핵심 이벤트</h4>
                      <ul className="events-list">
                        {selectedScenario.narrative.key_events.map((e, i) => (
                          <li key={i}>{e}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedScenario.narrative.plot_hooks.length > 0 && (
                    <div>
                      <h4>플롯 훅</h4>
                      <ul className="hooks-list">
                        {selectedScenario.narrative.plot_hooks.map((h, i) => (
                          <li key={i}>{h}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedScenario.narrative.previous_scenario_summary !== '없음' && (
                    <div>
                      <h4>이전 시나리오 요약</h4>
                      <div className="previous-summary">
                        {selectedScenario.narrative.previous_scenario_summary}
                      </div>
                    </div>
                  )}
                </div>
              </section>

              {/* 연결된 괴수 */}
              {selectedScenario.linked_beasts && selectedScenario.linked_beasts.length > 0 && (
                <section>
                  <h4>연결된 괴수</h4>
                  <div className="linked-beasts-list">
                    {selectedScenario.linked_beasts.map((b, i) => (
                      <span key={i} className="linked-beast-tag">
                        [{b.grade}] {b.title} ({b.species}) — {b.appearance_type}
                      </span>
                    ))}
                  </div>
                </section>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
