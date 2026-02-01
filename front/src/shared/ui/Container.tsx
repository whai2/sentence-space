import styled from '@emotion/styled';
import { theme } from '../lib/theme';

export const Container = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  background: ${theme.colors.background.main};
  border-radius: ${theme.borderRadius.xl};
  box-shadow: ${theme.shadows.lg};
  overflow: hidden;
`;

export const Header = styled.div`
  background: linear-gradient(135deg, ${theme.colors.primary.start} 0%, ${theme.colors.primary.end} 100%);
  color: white;
  padding: ${theme.spacing.xxl};
  text-align: center;

  h1 {
    font-size: 28px;
    margin-bottom: 10px;
  }

  p {
    opacity: 0.9;
    font-size: 14px;
  }
`;

export const Content = styled.div`
  padding: ${theme.spacing.xxl};
`;
