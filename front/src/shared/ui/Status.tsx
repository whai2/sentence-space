import styled from '@emotion/styled';
import { theme } from '../lib/theme';
import type { StreamStatus } from '../types/stream';

interface StatusBadgeProps {
  status: StreamStatus;
}

export const StatusBadge = styled.span<StatusBadgeProps>`
  padding: 6px ${theme.spacing.md};
  border-radius: ${theme.borderRadius.pill};
  font-size: 12px;
  font-weight: 600;

  ${({ status }) => {
    const color = theme.colors.status[status];
    const isStreaming = status === 'streaming';

    return `
      background: ${color};
      color: ${status === 'idle' ? theme.colors.text.secondary : 'white'};
      ${isStreaming ? 'animation: pulse 2s infinite;' : ''}
    `;
  }}
`;
