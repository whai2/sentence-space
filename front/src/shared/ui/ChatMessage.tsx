import styled from '@emotion/styled';
import { theme } from '../lib/theme';

export const MessageContainer = styled.div<{ role: 'user' | 'assistant'; isStreaming?: boolean }>`
  display: flex;
  gap: ${theme.spacing.md};
  align-items: flex-start;
  opacity: ${({ isStreaming }) => (isStreaming ? 0.8 : 1)};
  animation: ${({ isStreaming }) => (isStreaming ? 'pulse 2s infinite' : 'none')};

  @keyframes pulse {
    0%, 100% { opacity: 0.8; }
    50% { opacity: 1; }
  }
`;

export const Avatar = styled.div<{ role: 'user' | 'assistant' }>`
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: ${({ role }) => (role === 'user' ? theme.colors.primary.start : theme.colors.background.secondary)};
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  font-weight: 500;
  flex-shrink: 0;
`;

export const MessageBubble = styled.div<{ role: 'user' | 'assistant' }>`
  flex: 1;
  background: ${({ role }) => (role === 'user' ? '#e8e8e8' : theme.colors.background.light)};
  color: ${({ role }) => (role === 'user' ? '#1a1a1a' : theme.colors.text.primary)};
  padding: ${theme.spacing.md} ${theme.spacing.lg};
  border-radius: ${theme.borderRadius.lg};
  border-top-left-radius: ${({ role }) => (role === 'assistant' ? '4px' : theme.borderRadius.lg)};
  border-top-right-radius: ${({ role }) => (role === 'user' ? '4px' : theme.borderRadius.lg)};
  word-wrap: break-word;
  line-height: 1.5;
  max-width: 70%;

  ${({ role }) => role === 'user' && `
    margin-left: auto;
  `}

  /* Markdown 스타일링 */
  p {
    margin: 0.5em 0;
    &:first-of-type {
      margin-top: 0;
    }
    &:last-of-type {
      margin-bottom: 0;
    }
  }

  h1, h2, h3, h4, h5, h6 {
    margin: 0.8em 0 0.4em 0;
    font-weight: 600;
    &:first-of-type {
      margin-top: 0;
    }
  }

  h1 { font-size: 1.5em; }
  h2 { font-size: 1.3em; }
  h3 { font-size: 1.1em; }

  code {
    background: ${({ role }) => (role === 'user' ? 'rgba(0, 0, 0, 0.1)' : 'rgba(0, 0, 0, 0.05)')};
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 0.9em;
  }

  pre {
    background: ${({ role }) => (role === 'user' ? 'rgba(0, 0, 0, 0.1)' : 'rgba(0, 0, 0, 0.05)')};
    padding: ${theme.spacing.md};
    border-radius: ${theme.borderRadius.md};
    overflow-x: auto;
    margin: 0.5em 0;

    code {
      background: transparent;
      padding: 0;
    }
  }

  ul, ol {
    margin: 0.5em 0;
    padding-left: 1.5em;
  }

  li {
    margin: 0.25em 0;
  }

  blockquote {
    border-left: 3px solid ${({ role }) => (role === 'user' ? 'rgba(0, 0, 0, 0.2)' : theme.colors.primary.start)};
    padding-left: ${theme.spacing.md};
    margin: 0.5em 0;
    font-style: italic;
  }

  a {
    color: ${({ role }) => (role === 'user' ? '#0066cc' : theme.colors.primary.start)};
    text-decoration: underline;
    &:hover {
      opacity: 0.8;
    }
  }

  table {
    border-collapse: collapse;
    width: 100%;
    margin: 0.5em 0;
  }

  th, td {
    border: 1px solid ${({ role }) => (role === 'user' ? 'rgba(0, 0, 0, 0.15)' : 'rgba(0, 0, 0, 0.1)')};
    padding: 0.5em;
    text-align: left;
  }

  th {
    background: ${({ role }) => (role === 'user' ? 'rgba(0, 0, 0, 0.1)' : 'rgba(0, 0, 0, 0.05)')};
    font-weight: 600;
  }

  hr {
    border: none;
    border-top: 1px solid ${({ role }) => (role === 'user' ? 'rgba(0, 0, 0, 0.2)' : 'rgba(0, 0, 0, 0.1)')};
    margin: 1em 0;
  }

  img {
    max-width: 100%;
    height: auto;
    border-radius: ${theme.borderRadius.md};
  }
`;

export const MessageTime = styled.div`
  font-size: 12px;
  color: ${theme.colors.text.tertiary};
  margin-top: ${theme.spacing.xs};
  text-align: right;
`;

export const TypingIndicator = styled.div`
  display: flex;
  gap: 4px;
  padding: ${theme.spacing.md};

  span {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: ${theme.colors.text.tertiary};
    animation: typing 1.4s infinite ease-in-out;

    &:nth-of-type(1) { animation-delay: -0.32s; }
    &:nth-of-type(2) { animation-delay: -0.16s; }
  }

  @keyframes typing {
    0%, 80%, 100% {
      transform: scale(0);
      opacity: 0.5;
    }
    40% {
      transform: scale(1);
      opacity: 1;
    }
  }
`;