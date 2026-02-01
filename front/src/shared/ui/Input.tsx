import styled from '@emotion/styled';
import { theme } from '../lib/theme';

export const Input = styled.input`
  width: 100%;
  padding: ${theme.spacing.md};
  border: 2px solid ${theme.colors.border.default};
  border-radius: ${theme.borderRadius.lg};
  font-size: 14px;
  transition: ${theme.transitions.default};

  &:focus {
    outline: none;
    border-color: ${theme.colors.border.focus};
  }
`;

export const Textarea = styled.textarea`
  width: 100%;
  padding: ${theme.spacing.md};
  border: 2px solid ${theme.colors.border.default};
  border-radius: ${theme.borderRadius.lg};
  font-size: 14px;
  transition: ${theme.transitions.default};
  resize: vertical;
  min-height: 100px;
  font-family: inherit;

  &:focus {
    outline: none;
    border-color: ${theme.colors.border.focus};
  }
`;

export const Label = styled.label`
  display: block;
  margin-bottom: ${theme.spacing.sm};
  font-weight: 600;
  color: ${theme.colors.text.primary};
`;

export const FormGroup = styled.div`
  margin-bottom: ${theme.spacing.xl};
`;
