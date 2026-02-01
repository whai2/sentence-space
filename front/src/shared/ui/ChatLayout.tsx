import styled from '@emotion/styled';
import { theme } from '../lib/theme';

export const ChatContainer = styled.div`
  display: flex;
  height: 100vh;
  background: ${theme.colors.background.main};
  font-family: ${theme.fonts.primary};
`;

export const Sidebar = styled.div<{ isOpen: boolean }>`
  width: ${({ isOpen }) => (isOpen ? '280px' : '0')};
  min-width: ${({ isOpen }) => (isOpen ? '280px' : '0')};
  background: ${theme.colors.background.light};
  border-right: 1px solid ${theme.colors.border.default};
  transition: ${theme.transitions.default};
  overflow: hidden;
  display: flex;
  flex-direction: column;
`;

export const ChatMain = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
`;

export const ChatHeader = styled.header`
  padding: ${theme.spacing.md} ${theme.spacing.xl};
  border-bottom: 1px solid ${theme.colors.border.default};
  background: ${theme.colors.background.main};
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 60px;
`;

export const ChatContent = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

export const MessagesArea = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: ${theme.spacing.lg};
  display: flex;
  flex-direction: column;
  gap: ${theme.spacing.lg};
`;

export const InputArea = styled.div`
  padding: ${theme.spacing.lg};
  border-top: 1px solid ${theme.colors.border.default};
  background: ${theme.colors.background.main};
`;