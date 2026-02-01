import { useState, useRef, useEffect } from 'react';
import styled from '@emotion/styled';
import { theme } from '../../shared/lib/theme';
import {
  Container,
  Header,
  Content,
  Button,
  Input,
  Textarea,
  Label,
  FormGroup,
} from '../../shared/ui';
import { OutputSection, Statistics } from '../../features/stream-viewer';
import { StreamApi } from '../../shared/api/streamApi';
import type { StreamEvent, StreamStatus, StreamStats } from '../../shared/types/stream';

const InputSection = styled.div`
  margin-bottom: ${theme.spacing.xxl};
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 10px;
`;

export const StreamTestPage = () => {
  const [message, setMessage] = useState('ax dev task list를 정리해줄래?');
  const [conversationId, setConversationId] = useState('');
  const [apiUrl, setApiUrl] = useState('http://localhost:8000/api/v2/clickup/chat/stream');
  const [status, setStatus] = useState<StreamStatus>('idle');
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [stats, setStats] = useState<StreamStats>({
    nodeCount: 0,
    toolCount: 0,
    eventCount: 0,
  });
  const [isStreaming, setIsStreaming] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);

  const clearOutput = () => {
    setEvents([]);
    setStats({
      nodeCount: 0,
      toolCount: 0,
      eventCount: 0,
    });
    setStatus('idle');
  };

  const handleStream = async () => {
    if (isStreaming) {
      alert('이미 스트리밍이 진행 중입니다.');
      return;
    }

    if (!message.trim()) {
      alert('메시지를 입력해주세요.');
      return;
    }

    setIsStreaming(true);
    clearOutput();
    setStatus('streaming');

    const streamApi = new StreamApi(apiUrl);

    try {
      const request = {
        message: message.trim(),
        ...(conversationId.trim() && { conversation_id: conversationId.trim() }),
      };

      for await (const event of streamApi.streamChat(request)) {
        setEvents((prev) => [...prev, event]);

        setStats((prev) => ({
          eventCount: prev.eventCount + 1,
          nodeCount: prev.nodeCount + (event.event_type === 'node_start' ? 1 : 0),
          toolCount: prev.toolCount + (event.event_type === 'tool_result' ? 1 : 0),
        }));
      }

      setStatus('completed');
    } catch (error) {
      console.error('스트리밍 에러:', error);
      setStatus('error');

      const errorEvent: StreamEvent = {
        event_type: 'error',
        node_name: null,
        iteration: null,
        data: { error: (error as Error).message },
        timestamp: Date.now() / 1000,
      };
      setEvents((prev) => [...prev, errorEvent]);
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleStream();
    }
  };

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <Container>
      <Header>
        <h1>🚀 ClickUp 스트리밍 테스트</h1>
        <p>실시간으로 각 노드 실행 결과를 확인하세요</p>
      </Header>

      <Content>
        <InputSection>
          <FormGroup>
            <Label htmlFor="message">메시지</Label>
            <Textarea
              id="message"
              placeholder="예: ax dev task list를 정리해줄래?"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </FormGroup>

          <FormGroup>
            <Label htmlFor="conversationId">대화 ID (선택사항)</Label>
            <Input
              type="text"
              id="conversationId"
              placeholder="자동 생성됩니다"
              value={conversationId}
              onChange={(e) => setConversationId(e.target.value)}
            />
          </FormGroup>

          <FormGroup>
            <Label htmlFor="apiUrl">API URL</Label>
            <Input
              type="text"
              id="apiUrl"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
            />
          </FormGroup>

          <ButtonGroup>
            <Button
              variant="primary"
              disabled={isStreaming}
              onClick={handleStream}
            >
              {isStreaming ? '스트리밍 중...' : '스트리밍 시작'}
            </Button>
            <Button variant="secondary" onClick={clearOutput}>
              출력 지우기
            </Button>
          </ButtonGroup>
        </InputSection>

        <div ref={outputRef}>
          <OutputSection status={status} events={events} />
          <Statistics stats={stats} visible={stats.eventCount > 0} />
        </div>
      </Content>
    </Container>
  );
};
