import { useRef, useEffect } from 'react';
import styled from '@emotion/styled';
import { theme } from '../lib/theme';

const InputContainer = styled.div`
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: ${theme.spacing.md};
  background: white;
  border: 2px solid ${theme.colors.border.default};
  border-radius: ${theme.borderRadius.xl};
  padding: ${theme.spacing.md};
  transition: ${theme.transitions.fast};

  &:focus-within {
    border-color: ${theme.colors.border.focus};
    box-shadow: 0 0 0 3px ${theme.colors.border.focus}20;
  }
`;

const StyledTextarea = styled.textarea`
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-family: ${theme.fonts.primary};
  font-size: 16px;
  line-height: 1.5;
  padding: 0;
  background: transparent;
  max-height: 120px;
  min-height: 24px;

  &::placeholder {
    color: ${theme.colors.text.tertiary};
  }
`;

const SendButton = styled.button<{ disabled: boolean }>`
  width: 36px;
  height: 36px;
  border: none;
  background: ${({ disabled }) => (disabled ? theme.colors.text.tertiary : theme.colors.primary.start)};
  color: white;
  border-radius: 50%;
  cursor: ${({ disabled }) => (disabled ? 'not-allowed' : 'pointer')};
  display: flex;
  align-items: center;
  justify-content: center;
  transition: ${theme.transitions.fast};
  flex-shrink: 0;

  &:hover:not(:disabled) {
    background: ${theme.colors.primary.end};
    transform: scale(1.05);
  }

  &:active:not(:disabled) {
    transform: scale(0.95);
  }

  svg {
    width: 18px;
    height: 18px;
  }
`;

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput = ({ value, onChange, onSubmit, disabled = false, placeholder = "메시지를 입력하세요..." }: ChatInputProps) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (!disabled && value.trim()) {
        onSubmit();
      }
    }
  };

  const adjustHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  };

  useEffect(() => {
    adjustHeight();
  }, [value]);

  const canSubmit = !disabled && value.trim().length > 0;

  return (
    <InputContainer>
      <StyledTextarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
      />
      <SendButton
        type="button"
        onClick={onSubmit}
        disabled={!canSubmit}
        title="메시지 전송 (Enter)"
      >
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
        </svg>
      </SendButton>
    </InputContainer>
  );
};