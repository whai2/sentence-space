import { useState, useRef, useEffect } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000/api/v1'

interface Coordinate {
  lat: number
  lng: number
}

interface PlayerState {
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

interface GameState {
  session_id: string
  player: PlayerState
  turn_count: number
  threat_level: number
  discovered_locations: string[]
  game_over: boolean
  reached_destination: boolean
  quests: QuestState[]
  knowledge: KnowledgeItem[]
  active_bugs: BugInstance[]
}

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

type TabType = 'status' | 'quest' | 'knowledge'

// 두 좌표 간 거리 계산 (미터)
function calculateDistance(coord1: Coordinate, coord2: Coordinate): number {
  const R = 6371000 // 지구 반지름 (미터)
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

  const startGame = async () => {
    setIsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/game/session`, { method: 'POST' })
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
    if (!userMessage || !sessionId || isLoading) return

    setInput('')
    setChoices([])
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const res = await fetch(`${API_BASE}/game/play`, {
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

  if (!sessionId) {
    return (
      <div className="start-screen">
        <h1>붉은 사막</h1>
        <p>끝없이 펼쳐진 붉은 사막. 당신의 목표는 지하 도시를 찾는 것입니다.</p>
        <button onClick={startGame} disabled={isLoading}>
          {isLoading ? '로딩 중...' : '게임 시작'}
        </button>
      </div>
    )
  }

  return (
    <div className="game-container">
      {/* 사이드 패널 */}
      <aside className="side-panel">
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
            퀘스트
          </button>
          <button
            className={activeTab === 'knowledge' ? 'active' : ''}
            onClick={() => setActiveTab('knowledge')}
          >
            정보 ({gameState?.knowledge?.length || 0})
          </button>
        </div>

        {/* 탭 내용 */}
        <div className="tab-content">
          {activeTab === 'status' && gameState && (
            <>
              <div className="status-item">
                <span className="label">체력</span>
                <div className="health-bar">
                  <div
                    className="health-fill"
                    style={{ width: `${gameState.player.health}%` }}
                  />
                </div>
                <span>{gameState.player.health}/100</span>
              </div>

              <div className="status-item">
                <span className="label">위치</span>
                <span className="value">{gameState.player.position}</span>
              </div>

              <div className="status-item">
                <span className="label">좌표</span>
                <span className="value coords">
                  {gameState.player.coordinates?.lat.toFixed(4)}, {gameState.player.coordinates?.lng.toFixed(4)}
                </span>
              </div>

              <div className="status-item">
                <span className="label">출혈</span>
                <span className={`value ${gameState.player.bleeding ? 'danger' : ''}`}>
                  {gameState.player.bleeding ? '출혈 중!' : '없음'}
                </span>
              </div>

              <div className="status-item">
                <span className="label">위협</span>
                <span className="value">{gameState.threat_level}/10</span>
              </div>

              <div className="status-item">
                <span className="label">턴</span>
                <span className="value">{gameState.turn_count}</span>
              </div>

              {gameState.player.inventory.length > 0 && (
                <div className="inventory">
                  <span className="label">소지품</span>
                  <ul>
                    {gameState.player.inventory.map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 주변 벌레 정보 */}
              {gameState.active_bugs && gameState.active_bugs.length > 0 && (
                <div className="bugs-section">
                  <span className="label danger">⚠ 주변 벌레</span>
                  <ul className="bugs-list">
                    {gameState.active_bugs.map((bug) => {
                      const distance = gameState.player.coordinates
                        ? Math.round(calculateDistance(gameState.player.coordinates, bug.coordinates))
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

              {gameState.game_over && (
                <div className={`game-over ${gameState.reached_destination ? 'win' : 'lose'}`}>
                  {gameState.reached_destination ? '클리어!' : '게임 오버'}
                </div>
              )}
            </>
          )}

          {activeTab === 'quest' && gameState && (
            <div className="quest-list">
              {gameState.quests?.map((quest, i) => (
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
              {(!gameState.quests || gameState.quests.length === 0) && (
                <p className="empty-message">퀘스트가 없습니다.</p>
              )}
            </div>
          )}

          {activeTab === 'knowledge' && gameState && (
            <div className="knowledge-list">
              {gameState.knowledge?.map((item, i) => (
                <div key={i} className="knowledge-item">
                  <div className="knowledge-header">
                    <span className="knowledge-title">{item.title}</span>
                    <span className="knowledge-turn">턴 {item.turn_discovered}</span>
                  </div>
                  <p className="knowledge-content">{item.content}</p>
                  <span className="knowledge-location">발견: {item.discovered_at}</span>
                </div>
              ))}
              {(!gameState.knowledge || gameState.knowledge.length === 0) && (
                <p className="empty-message">아직 발견한 정보가 없습니다. 주변을 탐색해보세요.</p>
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
