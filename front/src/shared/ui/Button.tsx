import styled from '@emotion/styled';
import { theme } from '../lib/theme';

interface ButtonProps {
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

export const Button = styled.button<ButtonProps>`
  padding: ${theme.spacing.md} 24px;
  border: none;
  border-radius: ${theme.borderRadius.lg};
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: ${theme.transitions.default};
  flex: 1;

  ${({ variant = 'primary' }) =>
    variant === 'primary'
      ? `
    background: linear-gradient(135deg, ${theme.colors.primary.start} 0%, ${theme.colors.primary.end} 100%);
    color: white;

    &:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: ${theme.shadows.sm};
    }

    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  `
      : `
    background: ${theme.colors.background.light};
    color: ${theme.colors.text.primary};

    &:hover {
      background: ${theme.colors.border.hover};
    }
  `}
`;
