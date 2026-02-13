import { useState, useRef, useEffect } from 'react'
import './NarratorTestViewer.css'

const API_BASE = import.meta.env.VITE_API_BASE

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  charCount?: number
}

// 기본값: 전지적 독자 시점 세계관
const DEFAULT_WORLD_SETTING = `「전지적 독자 시점」 세계관.

어느 날, 세계가 소설이 되었다. 김독자가 유일하게 완독한 웹소설 「멸망 이후의 세 가지 방법」의 내용이 현실에서 그대로 재현되기 시작한다.

핵심 설정:
- "시나리오"가 현실을 지배한다. 도깨비들이 시나리오를 공지하고, 인간들은 시나리오를 클리어해야 생존할 수 있다.
- "성좌"들이 인간들의 행동을 관람하며, 코인(후원)을 보낸다.
- "스킬"과 "속성"이 존재하며, 시나리오를 클리어하면 보상을 받는다.
- 현재 시점: 1차 시나리오 직전. 서울 지하철 3호선. 아직 아무 일도 일어나지 않았다.`

const DEFAULT_CHARACTER_SHEET = `### 김독자 (주인공)
- 나이: 28세
- 성격: 냉정하고 분석적. 감정을 잘 드러내지 않는다. 하지만 내면에는 강한 의지.
- 말투: 짧고 건조한 문장. 내면 독백이 많다. 속으로는 냉소적.
- 현재 상태: 퇴근길 지하철에서 「멸망 이후의 세 가지 방법」을 막 완독. 소설의 결말에 묘한 감상을 느끼고 있다. 아직은 그저 소설일 뿐이라고 생각한다. 현실에서 무슨 일이 일어날지 전혀 모르는 상태.
- 특수: 소설 완독자. 소설의 전체 내용을 기억하고 있지만, 그것이 현실이 되리라고는 생각하지 않는다. 이상한 일이 벌어지면 데자뷰 같은 기시감을 느낄 수 있다.

### 유상아
- 나이: 22세, 대학생
- 성격: 활발하고 정의감이 강하다. 위기 상황에서도 남을 돕는 성향.
- 말투: 감정이 목소리에 그대로 드러남. 반말과 존댓말을 상황에 따라 섞어 사용.
- 현재 상태: 이어폰을 끼고 음악 듣는 중. 평범한 퇴근길.`

const NARRATIVE_STAGES = [
  '도입부 - 일상의 균열. 이상한 징후가 나타나기 시작한다.',
  '갈등 고조 - 시나리오가 공지되었다. 사람들이 혼란에 빠진다.',
  '클라이맥스 - 제한 시간이 다가온다. 결단을 내려야 한다.',
  '하강 - 위기가 지나갔다. 여파를 수습한다.',
  '결말 - 시나리오 클리어. 새로운 국면이 열린다.',
]

interface NarratorTestViewerProps {
  onBack: () => void
}

export default function NarratorTestViewer({ onBack }: NarratorTestViewerProps) {
  const [worldSetting, setWorldSetting] = useState(DEFAULT_WORLD_SETTING)
  const [characterSheet, setCharacterSheet] = useState(DEFAULT_CHARACTER_SHEET)
  const [narrativeStage, setNarrativeStage] = useState(NARRATIVE_STAGES[0])
  const [customStage, setCustomStage] = useState('')
  const [extraDirection, setExtraDirection] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [turnCount, setTurnCount] = useState(0)
  const [settingsOpen, setSettingsOpen] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const getLastNarrative = (): string => {
    const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant')
    return lastAssistant?.content || '(이것이 첫 장면입니다. 직전 장면은 없습니다.)'
  }

  const sendAction = async (action?: string) => {
    const playerAction = (action || input).trim()
    if (!playerAction || isLoading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: playerAction }])
    setIsLoading(true)

    try {
      const res = await fetch(`${API_BASE}/orv/v3/narrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          world_setting: worldSetting,
          character_sheet: characterSheet,
          narrative_stage: customStage || narrativeStage,
          previous_scene: getLastNarrative(),
          player_action: playerAction,
          extra_direction: extraDirection,
        }),
      })

      const data = await res.json()

      if (data.success) {
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: data.narrative,
            charCount: data.char_count,
          },
        ])
        setTurnCount(prev => prev + 1)
        setExtraDirection('')
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'system', content: `[오류] ${data.error || '서술 생성 실패'}` },
        ])
      }
    } catch (error) {
      console.error('narrate failed:', error)
      setMessages(prev => [
        ...prev,
        { role: 'system', content: `[연결 오류] 백엔드 서버를 확인하세요.` },
      ])
    }

    setIsLoading(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendAction()
    }
  }

  const resetChat = () => {
    setMessages([])
    setTurnCount(0)
    setExtraDirection('')
  }

  return (
    <div className="narrator-test">
      {/* 사이드 패널: 설정 */}
      <aside className={`narrator-settings ${settingsOpen ? 'open' : 'collapsed'}`}>
        <div className="settings-header">
          <button className="back-btn" onClick={onBack}>
            ← 돌아가기
          </button>
          <span className="settings-title">ORV v3 나레이터</span>
          <button
            className="toggle-btn"
            onClick={() => setSettingsOpen(!settingsOpen)}
          >
            {settingsOpen ? '접기' : '설정'}
          </button>
        </div>

        {settingsOpen && (
          <div className="settings-body">
            <div className="setting-group">
              <label>서사 단계</label>
              <select
                value={narrativeStage}
                onChange={e => {
                  setNarrativeStage(e.target.value)
                  setCustomStage('')
                }}
              >
                {NARRATIVE_STAGES.map((stage, i) => (
                  <option key={i} value={stage}>
                    {stage.split(' - ')[0]}
                  </option>
                ))}
                <option value="__custom__">직접 입력</option>
              </select>
              {narrativeStage === '__custom__' && (
                <textarea
                  className="custom-stage"
                  value={customStage}
                  onChange={e => setCustomStage(e.target.value)}
                  placeholder="서사 단계를 직접 입력..."
                  rows={2}
                />
              )}
            </div>

            <div className="setting-group">
              <label>추가 지시 (이번 턴만)</label>
              <textarea
                value={extraDirection}
                onChange={e => setExtraDirection(e.target.value)}
                placeholder="예: 도깨비의 등장을 서술해주세요..."
                rows={2}
              />
            </div>

            <div className="setting-group">
              <label>세계관 설정</label>
              <textarea
                value={worldSetting}
                onChange={e => setWorldSetting(e.target.value)}
                rows={6}
              />
            </div>

            <div className="setting-group">
              <label>캐릭터 시트</label>
              <textarea
                value={characterSheet}
                onChange={e => setCharacterSheet(e.target.value)}
                rows={6}
              />
            </div>
          </div>
        )}
      </aside>

      {/* 메인: 채팅 영역 */}
      <main className="narrator-chat">
        <div className="chat-header">
          <span>턴 {turnCount}</span>
          <span className="stage-badge">
            {(customStage || narrativeStage).split(' - ')[0]}
          </span>
          <button className="reset-btn" onClick={resetChat}>
            초기화
          </button>
        </div>

        <div className="narrator-messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <p>플레이어 행동을 입력하면 나레이터가 장면을 생성합니다.</p>
              <p className="hint">
                예: "스마트폰으로 소설을 읽고 있다. 지하철이 멈추자 주변을 관찰한다."
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`narrator-msg ${msg.role}`}>
              {msg.role === 'user' && (
                <div className="msg-label">플레이어 행동</div>
              )}
              <div className="msg-content">
                {msg.content.split('\n').map((line, j) => (
                  <span key={j}>
                    {line}
                    {j < msg.content.split('\n').length - 1 && <br />}
                  </span>
                ))}
              </div>
              {msg.charCount && (
                <div className="msg-meta">{msg.charCount}자</div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="narrator-msg assistant">
              <div className="msg-content loading-dots">생성 중...</div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="narrator-input-area">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="플레이어 행동을 입력하세요..."
            disabled={isLoading}
            rows={2}
          />
          <button onClick={() => sendAction()} disabled={isLoading || !input.trim()}>
            {isLoading ? '...' : '전송'}
          </button>
        </div>
      </main>
    </div>
  )
}
