export const theme = {
  colors: {
    primary: {
      start: '#667eea',
      end: '#764ba2',
    },
    background: {
      main: '#ffffff',
      dark: '#1e1e1e',
      secondary: '#252526',
      light: '#f5f5f5',
    },
    text: {
      primary: '#333',
      secondary: '#666',
      tertiary: '#858585',
      light: '#d4d4d4',
      code: '#4ec9b0',
      keyword: '#569cd6',
    },
    status: {
      idle: '#e0e0e0',
      streaming: '#4caf50',
      completed: '#2196f3',
      error: '#f44336',
      info: '#2196f3',
      success: '#4caf50',
      warning: '#ff9800',
    },
    event: {
      default: '#667eea',
      node_start: '#4caf50',
      tool_result: '#ff9800',
      node_end: '#2196f3',
      final: '#9c27b0',
      error: '#f44336',
    },
    border: {
      default: '#e0e0e0',
      focus: '#667eea',
      hover: '#e0e0e0',
    },
  },
  spacing: {
    xs: '5px',
    sm: '8px',
    md: '12px',
    lg: '15px',
    xl: '20px',
    xxl: '30px',
  },
  borderRadius: {
    sm: '4px',
    md: '6px',
    lg: '8px',
    xl: '12px',
    pill: '20px',
  },
  shadows: {
    sm: '0 5px 15px rgba(102, 126, 234, 0.4)',
    md: '0 10px 30px rgba(0, 0, 0, 0.2)',
    lg: '0 20px 60px rgba(0, 0, 0, 0.3)',
  },
  transitions: {
    default: 'all 0.3s',
    fast: 'all 0.15s',
  },
  fonts: {
    primary: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif',
    mono: '"Courier New", monospace',
  },
} as const;

export type Theme = typeof theme;
