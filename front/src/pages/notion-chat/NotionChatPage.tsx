import type { NotionChatConversation } from "@/entities/notion-chat";
import { notionChatKeys, NotionSessionApi, useAllNotionSessions } from "@/entities/notion-chat";
import styled from "@emotion/styled";
import { useQueries } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { NotionChatInterface } from "../../features/notion-chat";
import { theme } from "../../shared/lib/theme";
import { useNotionChatStore } from "../../shared/store/notionChatStore";
import {
  ChatContainer,
  ChatContent,
  ChatHeader,
  ChatMain,
  ConversationList,
  Sidebar,
} from "../../shared/ui";

const ToggleButton = styled.button`
  width: 40px;
  height: 40px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: ${theme.borderRadius.md};
  display: flex;
  align-items: center;
  justify-content: center;
  transition: ${theme.transitions.fast};

  &:hover {
    background: ${theme.colors.background.light};
  }

  svg {
    width: 24px;
    height: 24px;
    fill: ${theme.colors.text.primary};
  }
`;

const HeaderTitle = styled.h1`
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: ${theme.colors.text.primary};
`;

const HeaderControls = styled.div`
  display: flex;
  align-items: center;
  gap: ${theme.spacing.md};
`;

export const NotionChatPage = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const {
    conversations: localConversations,
    currentConversationId,
    createConversation,
    setCurrentConversation,
    addOrUpdateConversation,
    getCurrentConversation,
  } = useNotionChatStore();

  const { data: sessionsResponse, isLoading: isLoadingSessions } =
    useAllNotionSessions();

  const serverConversations = useMemo<NotionChatConversation[]>(() => {
    if (!sessionsResponse?.sessions) return [];
    return sessionsResponse.sessions.map((session) => ({
      id: session.session_id,
      title: undefined,
      messages: [],
      createdAt: new Date(session.created_at).getTime(),
      updatedAt: new Date(session.updated_at).getTime(),
    }));
  }, [sessionsResponse]);

  const conversations = useMemo(() => {
    const localIds = new Set(localConversations.map((c) => c.id));
    const serverOnly = serverConversations.filter((c) => !localIds.has(c.id));
    return [...localConversations, ...serverOnly].sort(
      (a, b) => b.updatedAt - a.updatedAt
    );
  }, [localConversations, serverConversations]);

  const sessionApi = useMemo(() => new NotionSessionApi(), []);
  const sessionChatsQueries = useQueries({
    queries: conversations.map((conversation) => ({
      queryKey: notionChatKeys.sessionChats(conversation.id, { limit: 100 }),
      queryFn: () =>
        sessionApi.getSessionChats(conversation.id, { limit: 100 }),
      enabled: !!conversation.id,
    })),
  });

  const conversationsWithMessages = useMemo(() => {
    return conversations.map((conversation, index) => {
      const chatsQuery = sessionChatsQueries[index];
      const chatsData = chatsQuery?.data;

      const isLocalConversation = localConversations.some(
        (c) => c.id === conversation.id
      );
      if (isLocalConversation && conversation.messages.length > 0) {
        return conversation;
      }

      if (chatsData?.chats) {
        const messages = chatsData.chats.flatMap((chat) => {
          const timestamp = new Date(chat.created_at).getTime();
          return [
            {
              id: `${chat.id}-user`,
              role: "user" as const,
              content: chat.user_message,
              timestamp,
            },
            {
              id: `${chat.id}-assistant`,
              role: "assistant" as const,
              content: chat.assistant_message,
              timestamp: timestamp + 1,
            },
          ];
        });

        return {
          ...conversation,
          messages,
        };
      }

      return conversation;
    });
  }, [conversations, sessionChatsQueries, localConversations]);

  const currentConversation = getCurrentConversation();

  const handleNewConversation = () => {
    const newId = createConversation();
    setCurrentConversation(newId);
  };

  const handleSelectConversation = (id: string) => {
    const selectedConversation = conversationsWithMessages.find(
      (conv) => conv.id === id
    );
    if (selectedConversation) {
      addOrUpdateConversation(selectedConversation);
    }
    setCurrentConversation(id);
  };

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  return (
    <ChatContainer>
      <Sidebar isOpen={sidebarOpen}>
        <ConversationList
          conversations={conversationsWithMessages}
          currentConversationId={currentConversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          isLoading={isLoadingSessions}
        />
      </Sidebar>

      <ChatMain>
        <ChatHeader>
          <HeaderControls>
            <ToggleButton onClick={toggleSidebar} title="사이드바 토글">
              <svg viewBox="0 0 24 24">
                <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z" />
              </svg>
            </ToggleButton>
            <HeaderTitle>{currentConversation?.title || "새 대화"}</HeaderTitle>
          </HeaderControls>

          <HeaderControls>
            <ToggleButton onClick={handleNewConversation} title="새 대화">
              <svg viewBox="0 0 24 24">
                <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
              </svg>
            </ToggleButton>
          </HeaderControls>
        </ChatHeader>

        <ChatContent>
          <NotionChatInterface />
        </ChatContent>
      </ChatMain>
    </ChatContainer>
  );
};
