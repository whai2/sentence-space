import type { ChatConversation } from "@/entities/chat";
import styled from "@emotion/styled";
import { theme } from "../lib/theme";

const ListContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
`;

const ListHeader = styled.div`
  padding: ${theme.spacing.lg};
  border-bottom: 1px solid ${theme.colors.border.default};
`;

const NewChatButton = styled.button`
  width: 100%;
  padding: ${theme.spacing.md};
  background: ${theme.colors.primary.start};
  color: white;
  border: none;
  border-radius: ${theme.borderRadius.lg};
  cursor: pointer;
  font-weight: 500;
  transition: ${theme.transitions.fast};

  &:hover {
    background: ${theme.colors.primary.end};
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(0);
  }
`;

const ConversationsContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: ${theme.spacing.md};
`;

const ConversationItem = styled.div<{ isActive: boolean }>`
  padding: ${theme.spacing.md};
  margin-bottom: ${theme.spacing.xs};
  border-radius: ${theme.borderRadius.lg};
  cursor: pointer;
  transition: ${theme.transitions.fast};
  background: ${({ isActive }) =>
    isActive ? theme.colors.primary.start : "transparent"};
  color: ${({ isActive }) => (isActive ? "white" : theme.colors.text.primary)};

  &:hover {
    background: ${({ isActive }) =>
      isActive ? theme.colors.primary.end : theme.colors.background.main};
  }
`;

const ConversationTitle = styled.div`
  font-weight: 500;
  margin-bottom: ${theme.spacing.xs};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const ConversationPreview = styled.div`
  font-size: 14px;
  opacity: 0.8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

const ConversationTime = styled.div`
  font-size: 12px;
  opacity: 0.6;
  margin-top: ${theme.spacing.xs};
`;

const EmptyState = styled.div`
  padding: ${theme.spacing.xl};
  text-align: center;
  color: ${theme.colors.text.tertiary};
  font-style: italic;
`;

interface ConversationListProps {
  conversations: ChatConversation[];
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  isLoading?: boolean;
}

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) {
    return date.toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } else if (days === 1) {
    return "어제";
  } else if (days < 7) {
    return `${days}일 전`;
  } else {
    return date.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
  }
};

const getPreviewText = (conversation: ChatConversation) => {
  const lastMessage = conversation.messages[conversation.messages.length - 1];
  if (!lastMessage) return "새 대화";

  // content를 문자열로 변환
  const contentString = typeof lastMessage.content === 'string'
    ? lastMessage.content
    : (lastMessage.content.data?.text || '');

  return contentString.length > 50
    ? `${contentString.slice(0, 50)}...`
    : contentString || "새 대화";
};

export const ConversationList = ({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  isLoading = false,
}: ConversationListProps) => {
  return (
    <ListContainer>
      <ListHeader>
        <NewChatButton onClick={onNewConversation}>+ 새 대화</NewChatButton>
      </ListHeader>

      <ConversationsContainer>
        {isLoading ? (
          <EmptyState>세션 목록을 불러오는 중...</EmptyState>
        ) : conversations.length === 0 ? (
          <EmptyState>
            대화가 없습니다.
            <br />새 대화를 시작해보세요!
          </EmptyState>
        ) : (
          conversations.map((conversation) => (
            <ConversationItem
              key={conversation.id}
              isActive={conversation.id === currentConversationId}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <ConversationTitle>
                {conversation.title || "새 대화"}
              </ConversationTitle>
              <ConversationPreview>
                {getPreviewText(conversation)}
              </ConversationPreview>
              <ConversationTime>
                {formatTime(conversation.updatedAt)}
              </ConversationTime>
            </ConversationItem>
          ))
        )}
      </ConversationsContainer>
    </ListContainer>
  );
};
