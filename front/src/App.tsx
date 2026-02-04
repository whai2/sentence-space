import { useState, useRef, useEffect } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000/api/v1'

type GameType = 'red-desert' | 'orv' | null

// === 붉은 사막 타입 ===
interface Coordinate {
  lat: number
  lng: number
}

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

// === 전독시 타입 ===
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

type GameState = RedDesertGameState | ORVGameState

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

type TabType = 'status' | 'quest' | 'knowledge' | 'constellation'

// 두 좌표 간 거리 계산 (미터)
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
  const [gameType, setGameType] = useState<GameType>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [gameState, setGameState] = useState<GameState | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [choices, setChoices] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<TabType>('status')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const startGame = async (type: GameType) => {
    if (!type) return
    setGameType(type)
    setIsLoading(true)

    const endpoint = type === 'red-desert' ? '/game/session' : '/orv/session'

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' })
      const data = await res.json()
      setSessionId(data.session_id)
      setGameState(data.state)
      setMessages([{ role: 'system', content: data.message }])
      setChoices(data.choices || [])
    } catch (error) {
      console.error('Failed to start game:', error)
    }
    setIsLoading(false)
  }

  const sendMessage = async (message?: string) => {
    const userMessage = (message || input).trim()
    if (!userMessage || !sessionId || isLoading || !gameType) return

    setInput('')
    setChoices([])
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    const endpoint = gameType === 'red-desert' ? '/game/play' : '/orv/play'

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, input: userMessage }),
      })
      const data = await res.json()
      setGameState(data.state)
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
      setChoices(data.choices || [])
    } catch (error) {
      console.error('Failed to send message:', error)
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

  // 게임 선택 화면
  if (!gameType) {
    return (
      <div className="select-screen">
        <h1>Sentence Space</h1>
        <p>텍스트 기반 TRPG 게임을 선택하세요</p>
        <div className="game-cards">
          <div className="game-card red-desert" onClick={() => startGame('red-desert')}>
            <h2>붉은 사막</h2>
            <p className="game-desc">
              거대한 모래폭풍에 쫓기고 있다.<br />
              뒤를 돌아볼 수 없다. 뒤에는 죽음뿐이다.<br />
              앞에는 끝없는 붉은 사막.
            </p>
            <span className="game-tag">생존</span>
          </div>
          <div className="game-card orv" onClick={() => startGame('orv')}>
            <h2>전지적 독자 시점</h2>
            <p className="game-desc">
              [시나리오가 현실화됩니다]<br />
              멈춰선 지하철. 눈앞에 뜬 푸른 창.<br />
              목표: 생명체 하나를 죽이시오.
            </p>
            <span className="game-tag">시나리오</span>
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
  const orvState = gameState as ORVGameState
  const redDesertState = gameState as RedDesertGameState

  return (
    <div className={`game-container ${gameType}`}>
      {/* 사이드 패널 */}
      <aside className="side-panel">
        <div className="panel-header">
          <button className="back-button" onClick={resetGame}>← 게임 선택</button>
          <span className="game-title">{isORV ? '전지적 독자 시점' : '붉은 사막'}</span>
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
            {isORV ? '시나리오' : '퀘스트'}
          </button>
          {isORV && (
            <button
              className={activeTab === 'constellation' ? 'active' : ''}
              onClick={() => setActiveTab('constellation')}
            >
              성좌
            </button>
          )}
          {!isORV && (
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
              {isORV ? (
                // 전독시 상태
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

                  {/* 스킬 */}
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

                  {/* 소지품 */}
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

                  {/* 주변 NPC */}
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
                </>
              ) : (
                // 붉은 사막 상태
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
                </>
              )}

              {gameState.game_over && (
                <div className={`game-over ${
                  isORV
                    ? (orvState.scenario_cleared ? 'win' : 'lose')
                    : (redDesertState.reached_destination ? 'win' : 'lose')
                }`}>
                  {isORV
                    ? (orvState.scenario_cleared ? '시나리오 클리어!' : '사망')
                    : (redDesertState.reached_destination ? '클리어!' : '게임 오버')}
                </div>
              )}
            </>
          )}

          {activeTab === 'quest' && gameState && (
            <div className="quest-list">
              {isORV ? (
                // 전독시 시나리오
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

          {activeTab === 'knowledge' && !isORV && redDesertState && (
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
      </main>
    </div>
  )
}

export default App
