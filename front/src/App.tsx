import { useState, useRef, useEffect } from 'react'
import './App.css'
import ScenarioGraphViewer from './components/ScenarioGraphViewer'
import MyeolsalViewer from './components/MyeolsalViewer'

const API_BASE = import.meta.env.VITE_API_BASE

type GameType = 'red-desert' | 'orv' | 'orv-v2' | 'myeolsal' | null

// === 공통 타입 ===
interface Coordinate {
  lat: number
  lng: number
}

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

// === ORV v2 타입 (새로 추가!) ===
interface ORVv2PlayerState {
  name: string
  level: number
  health: number
  max_health: number
  coins: number
  position: string
}

interface ORVv2GameState {
  session_id: string
  turn: number
  player: ORVv2PlayerState
  scenario: {
    title: string | null
    status: string | null
    remaining_time: number | null
  } | null
  game_over: boolean
}

interface ORVv2ActionResponse {
  success: boolean
  narrative: string
  choices: string[]
  scene_mood?: string
  game_state?: {
    turn: number
    health: number
    coins: number
    level: number
  }
  error?: string
  game_mode?: 'auto_narrative' | 'interactive'
  mode_changed?: boolean
}

// === 기존 타입들 (붉은 사막, ORV v1) ===
interface RedDesertPlayerState {
  health: number
  bleeding: boolean
  position: string
  coordinates: Coordinate
  inventory: string[]
}

interface BugInstance {
  id: string
  bug_type: string
  coordinates: Coordinate
  state: string
  target_player: boolean
}

interface QuestState {
  quest_id: string
  title: string
  status: string
  progress: string
}

interface KnowledgeItem {
  id: string
  title: string
  content: string
  discovered_at: string
  turn_discovered: number
}

interface RedDesertGameState {
  session_id: string
  player: RedDesertPlayerState
  turn_count: number
  threat_level: number
  discovered_locations: string[]
  game_over: boolean
  reached_destination: boolean
  quests: QuestState[]
  knowledge: KnowledgeItem[]
  active_bugs: BugInstance[]
}

interface ORVPlayerState {
  name: string
  level: number
  experience: number
  exp_to_next_level: number
  health: number
  max_health: number
  stamina: number
  coins: number
  attributes: {
    strength: number
    agility: number
    endurance: number
    magic: number
    luck: number
  }
  position: string
  coordinates: Coordinate
  skills: SkillInstance[]
  inventory: string[]
  fear_level: number
}

interface SkillInstance {
  skill_id: string
  name: string
  grade: string
  level: number
  description: string
  cooldown: number
}

interface ScenarioState {
  scenario_id: string
  title: string
  difficulty: string
  status: string
  objective: string
  progress: string
  remaining_time: number | null
  reward_coins: number
  reward_exp: number
}

interface NPCInstance {
  id: string
  name: string
  description: string
  position: string
  health: number
  is_alive: boolean
  disposition: string
  has_weapon: boolean
  weapon_type: string | null
}

interface ConstellationChannel {
  constellation_name: string
  message: string
  coins_donated: number
  turn: number
}

interface ORVGameState {
  session_id: string
  player: ORVPlayerState
  turn_count: number
  current_scenario: ScenarioState | null
  completed_scenarios: string[]
  npcs: NPCInstance[]
  killed_npcs: string[]
  constellation_channel: ConstellationChannel[]
  watching_constellations: string[]
  discovered_locations: string[]
  game_over: boolean
  scenario_cleared: boolean
  first_kill_completed: boolean
  panic_level: number
}

type GameState = RedDesertGameState | ORVGameState | ORVv2GameState

type TabType = 'status' | 'quest' | 'knowledge' | 'constellation'
type ChatViewType = 'chat' | 'graph'

// 두 좌표 간 거리 계산
function calculateDistance(coord1: Coordinate, coord2: Coordinate): number {
  const R = 6371000
  const lat1 = coord1.lat * Math.PI / 180
  const lat2 = coord2.lat * Math.PI / 180
  const deltaLat = (coord2.lat - coord1.lat) * Math.PI / 180
  const deltaLng = (coord2.lng - coord1.lng) * Math.PI / 180

  const a = Math.sin(deltaLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLng / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c
}

function App() {
  const [gameType, setGameType] = useState<GameType>('myeolsal')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [gameState, setGameState] = useState<GameState | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [choices, setChoices] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<TabType>('status')
  const [chatViewTab, setChatViewTab] = useState<ChatViewType>('chat')
  const [gameMode, setGameMode] = useState<'auto_narrative' | 'interactive'>('auto_narrative')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (message?: string) => {
    const userMessage = (message || input).trim()
    if (!userMessage || !sessionId || isLoading || !gameType) return

    setInput('')
    setChoices([])
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    let endpoint: string
    let body: any

    if (gameType === 'orv-v2') {
      // v2 API
      endpoint = `/orv/v2/sessions/${sessionId}/actions`
      body = { action: userMessage }
    } else if (gameType === 'red-desert') {
      endpoint = '/v1/game/play'
      body = { session_id: sessionId, input: userMessage }
    } else {
      endpoint = '/v1/orv/play'
      body = { session_id: sessionId, input: userMessage }
    }

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()

      if (gameType === 'orv-v2') {
        // v2 응답 처리
        const v2Data = data as ORVv2ActionResponse
        if (v2Data.success) {
          setMessages(prev => [...prev, { role: 'assistant', content: v2Data.narrative }])
          setChoices(v2Data.choices)
          // 게임 상태 업데이트
          if (v2Data.game_state) {
            setGameState(prev => {
              const v2State = prev as ORVv2GameState
              return {
                ...v2State,
                turn: v2Data.game_state!.turn,
                player: {
                  ...v2State.player,
                  health: v2Data.game_state!.health,
                  coins: v2Data.game_state!.coins,
                  level: v2Data.game_state!.level,
                }
              }
            })
          }

          // Handle mode transition
          if (v2Data.game_mode) {
            setGameMode(v2Data.game_mode)
          }

          if (v2Data.mode_changed && v2Data.game_mode === 'auto_narrative') {
            setMessages(prev => [...prev, {
              role: 'system',
              content: '[시나리오 완료] 자동 진행 모드로 전환됩니다.'
            }])
          }
        } else {
          setMessages(prev => [...prev, { role: 'system', content: `[오류] ${v2Data.error}` }])
          setChoices(['다시 시도하기'])
        }
      } else {
        // 기존 응답 처리
        setGameState(data.state)
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
        setChoices(data.choices || [])
      }
    } catch (error) {
      console.error('Failed to send message:', error)
      setMessages(prev => [...prev, { role: 'system', content: '오류가 발생했습니다.' }])
    }
    setIsLoading(false)
  }

  const continueAutoNarrative = async () => {
    if (!sessionId || isLoading || gameType !== 'orv-v2') return

    setIsLoading(true)
    setChoices([])

    try {
      const res = await fetch(`${API_BASE}/orv/v2/sessions/${sessionId}/continue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const data = await res.json() as ORVv2ActionResponse

      if (data.success) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.narrative }])
        setChoices(data.choices)

        // Update game state
        if (data.game_state) {
          setGameState(prev => ({
            ...prev as ORVv2GameState,
            turn: data.game_state!.turn,
            player: {
              ...(prev as ORVv2GameState).player,
              health: data.game_state!.health,
              coins: data.game_state!.coins,
              level: data.game_state!.level,
            }
          }))
        }

        // Handle mode transition
        if (data.game_mode) {
          setGameMode(data.game_mode)
        }

        if (data.mode_changed && data.game_mode === 'interactive') {
          setMessages(prev => [...prev, {
            role: 'system',
            content: '[시나리오 시작] 이제 행동을 선택하세요.'
          }])
        }
      } else {
        setMessages(prev => [...prev, { role: 'system', content: `[오류] ${data.error}` }])
      }
    } catch (error) {
      console.error('Failed to continue:', error)
      setMessages(prev => [...prev, { role: 'system', content: '오류가 발생했습니다.' }])
    }
    setIsLoading(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const handleChoiceClick = (choice: string) => {
    sendMessage(choice)
  }

  const resetGame = () => {
    setGameType(null)
    setSessionId(null)
    setGameState(null)
    setMessages([])
    setChoices([])
    setInput('')
    setActiveTab('status')
  }

  // 멸살법 뷰어 (게임이 아닌 도감)
  if (gameType === 'myeolsal') {
    return <MyeolsalViewer onBack={() => setGameType(null)} />
  }

  // 게임 선택 화면
  if (!gameType) {
    return (
      <div className="select-screen">
        <h1>Sentence Space</h1>
        <p>전지적 독자 시점 세계관</p>
        <div className="game-cards">
          <div className="game-card myeolsal" onClick={() => setGameType('myeolsal')}>
            <h2>tls123의 괴수 백과</h2>
            <p className="game-desc">
              [멸살법 저자의 신간]<br />
              tls123이 집필한 생존 가이드.<br />
              괴수 정보 검색 및 열람.
            </p>
            <span className="game-tag myeolsal">도감</span>
          </div>
        </div>
      </div>
    )
  }

  // 세션 로딩 중
  if (!sessionId) {
    return (
      <div className="start-screen">
        <div className="loading-spinner" />
        <p>게임 로딩 중...</p>
      </div>
    )
  }

  const isORV = gameType === 'orv'
  const isORVv2 = gameType === 'orv-v2'
  const orvState = gameState as ORVGameState
  const orvV2State = gameState as ORVv2GameState
  const redDesertState = gameState as RedDesertGameState

  return (
    <div className={`game-container ${gameType}`}>
      {/* 사이드 패널 */}
      <aside className="side-panel">
        <div className="panel-header">
          <button className="back-button" onClick={resetGame}>← 게임 선택</button>
          <span className="game-title">
            {isORVv2 ? '전지적 독자 시점 v2' : isORV ? '전지적 독자 시점' : '붉은 사막'}
          </span>
        </div>

        {/* 탭 버튼 */}
        <div className="tab-buttons">
          <button
            className={activeTab === 'status' ? 'active' : ''}
            onClick={() => setActiveTab('status')}
          >
            상태
          </button>
          <button
            className={activeTab === 'quest' ? 'active' : ''}
            onClick={() => setActiveTab('quest')}
          >
            {(isORV || isORVv2) ? '시나리오' : '퀘스트'}
          </button>
          {isORV && (
            <button
              className={activeTab === 'constellation' ? 'active' : ''}
              onClick={() => setActiveTab('constellation')}
            >
              성좌
            </button>
          )}
          {!isORV && !isORVv2 && (
            <button
              className={activeTab === 'knowledge' ? 'active' : ''}
              onClick={() => setActiveTab('knowledge')}
            >
              정보 ({redDesertState?.knowledge?.length || 0})
            </button>
          )}
        </div>

        {/* 탭 내용 */}
        <div className="tab-content">
          {activeTab === 'status' && gameState && (
            <>
              {isORVv2 ? (
                // ORV v2 상태 (간소화)
                <>
                  <div className="status-item">
                    <span className="label">이름</span>
                    <span className="value">{orvV2State.player.name}</span>
                  </div>
                  <div className="status-item">
                    <span className="label">레벨</span>
                    <span className="value level">Lv.{orvV2State.player.level}</span>
                  </div>
                  <div className="status-item">
                    <span className="label">체력</span>
                    <div className="health-bar">
                      <div
                        className="health-fill"
                        style={{ width: `${(orvV2State.player.health / orvV2State.player.max_health) * 100}%` }}
                      />
                    </div>
                    <span>{orvV2State.player.health}/{orvV2State.player.max_health}</span>
                  </div>
                  <div className="status-item coins">
                    <span className="label">코인</span>
                    <span className="value coin-value">{orvV2State.player.coins}</span>
                  </div>
                  <div className="status-item">
                    <span className="label">위치</span>
                    <span className="value">{orvV2State.player.position}</span>
                  </div>
                  <div className="status-item">
                    <span className="label">턴</span>
                    <span className="value">{orvV2State.turn}</span>
                  </div>

                  {orvV2State.game_over && (
                    <div className="game-over lose">
                      게임 오버
                    </div>
                  )}
                </>
              ) : isORV ? (
                // ORV v1 상태 (기존 코드 유지)
                <>
                  <div className="status-item">
                    <span className="label">레벨</span>
                    <span className="value level">Lv.{orvState.player.level}</span>
                  </div>
                  <div className="status-item">
                    <span className="label">체력</span>
                    <div className="health-bar">
                      <div
                        className="health-fill"
                        style={{ width: `${(orvState.player.health / orvState.player.max_health) * 100}%` }}
                      />
                    </div>
                    <span>{orvState.player.health}/{orvState.player.max_health}</span>
                  </div>
                  <div className="status-item">
                    <span className="label">스태미나</span>
                    <div className="stamina-bar">
                      <div
                        className="stamina-fill"
                        style={{ width: `${orvState.player.stamina}%` }}
                      />
                    </div>
                    <span>{orvState.player.stamina}/100</span>
                  </div>
                  <div className="status-item coins">
                    <span className="label">코인</span>
                    <span className="value coin-value">{orvState.player.coins}</span>
                  </div>
                  <div className="status-item">
                    <span className="label">공포도</span>
                    <span className={`value ${orvState.player.fear_level >= 70 ? 'danger' : ''}`}>
                      {orvState.player.fear_level}/100
                    </span>
                  </div>
                  <div className="status-item">
                    <span className="label">위치</span>
                    <span className="value">{orvState.player.position}</span>
                  </div>
                  <div className="status-item">
                    <span className="label">턴</span>
                    <span className="value">{orvState.turn_count}</span>
                  </div>

                  {orvState.player.skills.length > 0 && (
                    <div className="skills-section">
                      <span className="label">스킬</span>
                      <ul className="skills-list">
                        {orvState.player.skills.map((skill, i) => (
                          <li key={i} className={`skill-item ${skill.grade}`}>
                            <span className="skill-name">{skill.name}</span>
                            <span className="skill-grade">[{skill.grade}]</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {orvState.player.inventory.length > 0 && (
                    <div className="inventory">
                      <span className="label">소지품</span>
                      <ul>
                        {orvState.player.inventory.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {orvState.npcs.filter(n => n.position === orvState.player.position && n.is_alive).length > 0 && (
                    <div className="npcs-section">
                      <span className="label">주변 인물</span>
                      <ul className="npcs-list">
                        {orvState.npcs
                          .filter(n => n.position === orvState.player.position && n.is_alive)
                          .map((npc) => (
                            <li key={npc.id} className={`npc-item ${npc.disposition}`}>
                              <span className="npc-name">{npc.name}</span>
                              <span className={`npc-disposition ${npc.disposition}`}>
                                {npc.disposition === 'hostile' ? '적대' :
                                  npc.disposition === 'terrified' ? '공포' :
                                    npc.disposition === 'friendly' ? '우호' : '중립'}
                              </span>
                            </li>
                          ))}
                      </ul>
                    </div>
                  )}

                  {orvState.game_over && (
                    <div className={`game-over ${orvState.scenario_cleared ? 'win' : 'lose'}`}>
                      {orvState.scenario_cleared ? '시나리오 클리어!' : '사망'}
                    </div>
                  )}
                </>
              ) : (
                // 붉은 사막 상태 (기존 코드)
                <>
                  <div className="status-item">
                    <span className="label">체력</span>
                    <div className="health-bar">
                      <div
                        className="health-fill"
                        style={{ width: `${redDesertState.player.health}%` }}
                      />
                    </div>
                    <span>{redDesertState.player.health}/100</span>
                  </div>

                  <div className="status-item">
                    <span className="label">위치</span>
                    <span className="value">{redDesertState.player.position}</span>
                  </div>

                  <div className="status-item">
                    <span className="label">출혈</span>
                    <span className={`value ${redDesertState.player.bleeding ? 'danger' : ''}`}>
                      {redDesertState.player.bleeding ? '출혈 중!' : '없음'}
                    </span>
                  </div>

                  <div className="status-item">
                    <span className="label">위협</span>
                    <span className="value">{redDesertState.threat_level}/10</span>
                  </div>

                  <div className="status-item">
                    <span className="label">턴</span>
                    <span className="value">{redDesertState.turn_count}</span>
                  </div>

                  {redDesertState.player.inventory.length > 0 && (
                    <div className="inventory">
                      <span className="label">소지품</span>
                      <ul>
                        {redDesertState.player.inventory.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {redDesertState.active_bugs && redDesertState.active_bugs.length > 0 && (
                    <div className="bugs-section">
                      <span className="label danger">⚠ 주변 벌레</span>
                      <ul className="bugs-list">
                        {redDesertState.active_bugs.map((bug) => {
                          const distance = redDesertState.player.coordinates
                            ? Math.round(calculateDistance(redDesertState.player.coordinates, bug.coordinates))
                            : 0
                          return (
                            <li key={bug.id} className={`bug-item ${bug.state}`}>
                              <span className="bug-name">{bug.bug_type}</span>
                              <span className="bug-distance">{distance}m</span>
                              <span className={`bug-state ${bug.state}`}>
                                {bug.state === 'chasing' ? '추격 중!' : '순찰 중'}
                              </span>
                            </li>
                          )
                        })}
                      </ul>
                    </div>
                  )}

                  {redDesertState.game_over && (
                    <div className={`game-over ${redDesertState.reached_destination ? 'win' : 'lose'}`}>
                      {redDesertState.reached_destination ? '클리어!' : '게임 오버'}
                    </div>
                  )}
                </>
              )}
            </>
          )}

          {activeTab === 'quest' && gameState && (
            <div className="quest-list">
              {isORVv2 ? (
                // ORV v2 시나리오
                orvV2State.scenario ? (
                  <div className="quest-item scenario active">
                    <div className="quest-header">
                      <span className="quest-status active">진행 중</span>
                      <span className="quest-title">{orvV2State.scenario.title}</span>
                    </div>
                    {orvV2State.scenario.remaining_time !== null && (
                      <p className="quest-progress">
                        남은 시간: {orvV2State.scenario.remaining_time}턴
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="empty-message">활성 시나리오 없음</p>
                )
              ) : isORV ? (
                // ORV v1 시나리오
                orvState.current_scenario ? (
                  <div className={`quest-item scenario ${orvState.current_scenario.status}`}>
                    <div className="quest-header">
                      <span className={`quest-status ${orvState.current_scenario.status}`}>
                        {orvState.current_scenario.difficulty}급
                      </span>
                      <span className="quest-title">{orvState.current_scenario.title}</span>
                    </div>
                    <p className="quest-objective">{orvState.current_scenario.objective}</p>
                    <p className="quest-progress">{orvState.current_scenario.progress}</p>
                    <div className="quest-reward">
                      보상: {orvState.current_scenario.reward_coins} 코인 / {orvState.current_scenario.reward_exp} EXP
                    </div>
                  </div>
                ) : (
                  <p className="empty-message">활성 시나리오 없음</p>
                )
              ) : (
                // 붉은 사막 퀘스트
                <>
                  {redDesertState.quests?.map((quest, i) => (
                    <div key={i} className={`quest-item ${quest.status}`}>
                      <div className="quest-header">
                        <span className={`quest-status ${quest.status}`}>
                          {quest.status === 'active' ? '진행 중' : quest.status === 'completed' ? '완료' : '실패'}
                        </span>
                        <span className="quest-title">{quest.title}</span>
                      </div>
                      <p className="quest-progress">{quest.progress}</p>
                    </div>
                  ))}
                  {(!redDesertState.quests || redDesertState.quests.length === 0) && (
                    <p className="empty-message">퀘스트가 없습니다.</p>
                  )}
                </>
              )}
            </div>
          )}

          {activeTab === 'constellation' && isORV && orvState && (
            <div className="constellation-list">
              <div className="watching-section">
                <span className="label">관전 중인 성좌</span>
                <ul className="watching-list">
                  {orvState.watching_constellations.map((name, i) => (
                    <li key={i}>{name.replace(/_/g, ' ')}</li>
                  ))}
                </ul>
              </div>
              <div className="channel-section">
                <span className="label">성좌 채널</span>
                {orvState.constellation_channel.length > 0 ? (
                  <ul className="channel-messages">
                    {orvState.constellation_channel.slice(-10).reverse().map((msg, i) => (
                      <li key={i} className="channel-message">
                        <span className="constellation-name">[{msg.constellation_name}]</span>
                        <span className="message-text">{msg.message}</span>
                        {msg.coins_donated > 0 && (
                          <span className="donation">+{msg.coins_donated} 코인</span>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="empty-message">아직 성좌들의 반응이 없습니다.</p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'knowledge' && !isORV && !isORVv2 && redDesertState && (
            <div className="knowledge-list">
              {redDesertState.knowledge?.map((item, i) => (
                <div key={i} className="knowledge-item">
                  <div className="knowledge-header">
                    <span className="knowledge-title">{item.title}</span>
                    <span className="knowledge-turn">턴 {item.turn_discovered}</span>
                  </div>
                  <p className="knowledge-content">{item.content}</p>
                  <span className="knowledge-location">발견: {item.discovered_at}</span>
                </div>
              ))}
              {(!redDesertState.knowledge || redDesertState.knowledge.length === 0) && (
                <p className="empty-message">아직 발견한 정보가 없습니다.</p>
              )}
            </div>
          )}
        </div>
      </aside>

      {/* 채팅 영역 */}
      <main className="chat-area">
        {chatViewTab === 'chat' ? (
          <>
            <div className="messages">
              {messages.map((msg, i) => (
                <div key={i} className={`message ${msg.role}`}>
                  <div className="message-content">{msg.content}</div>
                </div>
              ))}
              {isLoading && (
                <div className="message assistant">
                  <div className="message-content loading">...</div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* 선택지 영역 */}
            {choices.length > 0 && !isLoading && !gameState?.game_over && (
              <div className="choices-area">
                {choices.map((choice, i) => (
                  <button
                    key={i}
                    className="choice-button"
                    onClick={() => handleChoiceClick(choice)}
                  >
                    {choice}
                  </button>
                ))}
              </div>
            )}

            {/* ORV v2 specific input */}
            {gameType === 'orv-v2' && !gameState?.game_over && (
              <div className="input-area">
                {gameMode === 'auto_narrative' ? (
                  // Auto mode: Continue button only
                  <button
                    className="continue-button"
                    onClick={continueAutoNarrative}
                    disabled={isLoading}
                  >
                    {isLoading ? '진행 중...' : '진행하기'}
                  </button>
                ) : (
                  // Interactive mode: Text input + choices
                  <>
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="행동을 입력하세요..."
                      disabled={isLoading}
                      rows={2}
                    />
                    <button
                      onClick={() => sendMessage()}
                      disabled={isLoading || !input.trim()}
                    >
                      전송
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Other games: original input */}
            {gameType !== 'orv-v2' && (
              <div className="input-area">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="또는 직접 입력..."
                  disabled={isLoading || gameState?.game_over}
                  rows={2}
                />
                <button
                  onClick={() => sendMessage()}
                  disabled={isLoading || !input.trim() || gameState?.game_over}
                >
                  전송
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="graph-view-container">
            <ScenarioGraphViewer />
          </div>
        )}

        {/* ORV v2: Chat view tabs (bottom) */}
        {isORVv2 && (
          <div className="chat-view-tabs">
            <button
              className={chatViewTab === 'chat' ? 'active' : ''}
              onClick={() => setChatViewTab('chat')}
            >
              채팅
            </button>
            <button
              className={chatViewTab === 'graph' ? 'active' : ''}
              onClick={() => setChatViewTab('graph')}
            >
              지식 그래프
            </button>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
