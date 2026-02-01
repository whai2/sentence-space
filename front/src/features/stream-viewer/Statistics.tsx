import styled from '@emotion/styled';
import { theme } from '../../shared/lib/theme';
import type { StreamStats } from '../../shared/types/stream';

interface StatisticsProps {
  stats: StreamStats;
  visible: boolean;
}

const StatsContainer = styled.div<{ visible: boolean }>`
  display: ${({ visible }) => (visible ? 'grid' : 'none')};
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: ${theme.spacing.lg};
  margin-top: ${theme.spacing.xl};
`;

const StatCard = styled.div`
  background: ${theme.colors.background.light};
  padding: ${theme.spacing.lg};
  border-radius: ${theme.borderRadius.lg};
  text-align: center;
`;

const StatValue = styled.div`
  font-size: 24px;
  font-weight: 700;
  color: ${theme.colors.primary.start};
`;

const StatLabel = styled.div`
  font-size: 12px;
  color: ${theme.colors.text.secondary};
  margin-top: ${theme.spacing.xs};
`;

export const Statistics = ({ stats, visible }: StatisticsProps) => {
  return (
    <StatsContainer visible={visible}>
      <StatCard>
        <StatValue>{stats.nodeCount}</StatValue>
        <StatLabel>실행된 노드</StatLabel>
      </StatCard>
      <StatCard>
        <StatValue>{stats.toolCount}</StatValue>
        <StatLabel>도구 실행</StatLabel>
      </StatCard>
      <StatCard>
        <StatValue>{stats.eventCount}</StatValue>
        <StatLabel>총 이벤트</StatLabel>
      </StatCard>
    </StatsContainer>
  );
};
