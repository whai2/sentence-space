import styled from '@emotion/styled';
import { theme } from '../../shared/lib/theme';
import { StatusBadge } from '../../shared/ui';
import type { StreamEvent, StreamStatus } from '../../shared/types/stream';
import { EventCard } from './EventCard';

interface OutputSectionProps {
  status: StreamStatus;
  events: StreamEvent[];
}

const OutputContainer = styled.div`
  margin-top: ${theme.spacing.xxl};
`;

const OutputHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: ${theme.spacing.lg};

  h2 {
    font-size: 20px;
    color: ${theme.colors.text.primary};
  }
`;

const OutputContent = styled.div`
  background: ${theme.colors.background.dark};
  color: ${theme.colors.text.light};
  padding: ${theme.spacing.xl};
  border-radius: ${theme.borderRadius.lg};
  min-height: 400px;
  max-height: 600px;
  overflow-y: auto;
  font-family: ${theme.fonts.mono};
  font-size: 13px;
  line-height: 1.6;
`;

const getStatusText = (status: StreamStatus): string => {
  const statusTexts: Record<StreamStatus, string> = {
    idle: '대기 중',
    streaming: '스트리밍 중',
    completed: '완료',
    error: '에러 발생',
  };
  return statusTexts[status];
};

export const OutputSection = ({ status, events }: OutputSectionProps) => {
  return (
    <OutputContainer>
      <OutputHeader>
        <h2>실시간 출력</h2>
        <StatusBadge status={status}>{getStatusText(status)}</StatusBadge>
      </OutputHeader>
      <OutputContent>
        {events.map((event, index) => (
          <EventCard key={index} event={event} />
        ))}
      </OutputContent>
    </OutputContainer>
  );
};
