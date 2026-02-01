import { Global, css } from '@emotion/react';
import { theme } from '@/shared/lib/theme';

const globalStyles = css`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: ${theme.fonts.primary};
    background: linear-gradient(
      135deg,
      ${theme.colors.primary.start} 0%,
      ${theme.colors.primary.end} 100%
    );
    min-height: 100vh;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.7;
    }
  }
`;

interface GlobalStyleProviderProps {
  children: React.ReactNode;
}

export const GlobalStyleProvider = ({ children }: GlobalStyleProviderProps) => {
  return (
    <>
      <Global styles={globalStyles} />
      {children}
    </>
  );
};
