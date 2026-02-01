import styled from '@emotion/styled';
import { theme } from '../../shared/lib/theme';
import type { StreamEvent } from '../../shared/types/stream';

interface EventCardProps {
  event: StreamEvent;
}

const EventContainer = styled.div<{ eventType: string }>`
  margin-bottom: ${theme.spacing.lg};
  padding: ${theme.spacing.md};
  background: ${theme.colors.background.secondary};
  border-radius: ${theme.borderRadius.md};
  border-left: 4px solid ${({ eventType }) =>
    theme.colors.event[eventType as keyof typeof theme.colors.event] ||
    theme.colors.event.default};
`;

const EventHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: ${theme.spacing.sm};
`;

const EventType = styled.span`
  font-weight: 600;
  color: ${theme.colors.text.code};
  text-transform: uppercase;
`;

const EventNode = styled.span`
  color: ${theme.colors.text.keyword};
  font-size: 12px;
  margin-left: 10px;
`;

const EventTime = styled.span`
  font-size: 11px;
  color: ${theme.colors.text.tertiary};
`;

const MessageContainer = styled.div`
  margin-top: ${theme.spacing.sm};
`;

const MessageText = styled.div`
  padding: ${theme.spacing.md};
  background: ${theme.colors.background.dark};
  border-radius: ${theme.borderRadius.sm};
  color: ${theme.colors.text.light};
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
`;

const ToolResult = styled.div`
  margin-top: ${theme.spacing.sm};
  padding: ${theme.spacing.md};
  background: ${theme.colors.background.dark};
  border-radius: ${theme.borderRadius.sm};

  pre {
    margin: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-family: ${theme.fonts.mono};
    font-size: 13px;
    color: ${theme.colors.text.light};
  }
`;

const StatusBadge = styled.span<{ status: 'start' | 'end' | 'processing' }>`
  display: inline-block;
  padding: 4px 12px;
  border-radius: ${theme.borderRadius.sm};
  font-size: 12px;
  font-weight: 500;
  background: ${({ status }) => {
    switch (status) {
      case 'start':
        return theme.colors.status.info;
      case 'end':
        return theme.colors.status.success;
      case 'processing':
        return theme.colors.status.warning;
      default:
        return theme.colors.status.info;
    }
  }};
  color: white;
`;

const ErrorMessage = styled.div`
  padding: ${theme.spacing.md};
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid ${theme.colors.status.error};
  border-radius: ${theme.borderRadius.sm};
  color: ${theme.colors.status.error};
  margin-top: ${theme.spacing.sm};
`;

// 이벤트 타입별 한글 레이블
const getEventTypeLabel = (eventType: string): string => {
  const labels: Record<string, string> = {
    node_start: '시작',
    node_end: '완료',
    tool_result: '도구 실행 결과',
    final: '최종 응답',
    error: '에러',
  };
  return labels[eventType] || eventType;
};

// 메시지 추출 함수
const extractMessage = (data: Record<string, any> | undefined | null): string | null => {
  if (!data || typeof data !== 'object') {
    return null;
  }

  // message 필드 직접 확인
  if (data.message && typeof data.message === 'string') {
    return data.message;
  }

  // content 필드 확인
  if (data.content && typeof data.content === 'string') {
    return data.content;
  }

  // messages 배열 확인
  if (Array.isArray(data.messages) && data.messages.length > 0) {
    const lastMessage = data.messages[data.messages.length - 1];
    if (typeof lastMessage === 'string') {
      return lastMessage;
    }
    if (lastMessage?.content) {
      return lastMessage.content;
    }
  }

  // output 필드 확인
  if (data.output && typeof data.output === 'string') {
    return data.output;
  }

  // result 필드 확인
  if (data.result && typeof data.result === 'string') {
    return data.result;
  }

  return null;
};

export const EventCard = ({ event }: EventCardProps) => {
  const formatTime = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString();
  };

  const message = extractMessage(event.data);
  const showRawData = !message && event.event_type !== 'node_start' && event.event_type !== 'node_end';

  return (
    <EventContainer eventType={event.event_type}>
      <EventHeader>
        <div>
          <EventType>{getEventTypeLabel(event.event_type)}</EventType>
          {event.node_name && <EventNode>[{event.node_name}]</EventNode>}
        </div>
        <EventTime>{formatTime(event.timestamp ?? Date.now() / 1000)}</EventTime>
      </EventHeader>

      <MessageContainer>
        {/* 에러 메시지 */}
        {event.event_type === 'error' && event.data?.error && (
          <ErrorMessage>
            {typeof event.data.error === 'string' ? event.data.error : JSON.stringify(event.data.error)}
          </ErrorMessage>
        )}

        {/* 노드 시작/종료는 상태 뱃지만 표시 */}
        {event.event_type === 'node_start' && (
          <StatusBadge status="start">처리 시작</StatusBadge>
        )}

        {event.event_type === 'node_end' && (
          <StatusBadge status="end">처리 완료</StatusBadge>
        )}

        {/* 메시지가 있는 경우 텍스트로 표시 */}
        {message && event.event_type !== 'error' && (
          <MessageText>{message}</MessageText>
        )}

        {/* 도구 실행 결과나 기타 데이터는 JSON으로 표시 */}
        {showRawData && event.data && (
          <ToolResult>
            <pre>{JSON.stringify(event.data, null, 2)}</pre>
          </ToolResult>
        )}
      </MessageContainer>
    </EventContainer>
  );
};
