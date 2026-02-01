import type {
  NotionChatConversation,
  NotionChatMessage,
  NotionChatState,
  NotionChatStatus,
} from "@/entities/notion-chat";
import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";

interface NotionChatStore extends NotionChatState {
  status: NotionChatStatus;

  // Actions
  createConversation: () => string;
  setCurrentConversation: (id: string | null) => void;
  addOrUpdateConversation: (conversation: NotionChatConversation) => void;
  addMessage: (
    conversationId: string,
    message: Omit<NotionChatMessage, "id" | "timestamp">
  ) => string;
  updateMessage: (
    conversationId: string,
    messageId: string,
    updates: Partial<NotionChatMessage>
  ) => void;
  appendMessageContent: (
    conversationId: string,
    messageId: string,
    content: string
  ) => void;
  deleteConversation: (id: string) => void;
  clearAllConversations: () => void;
  setStatus: (status: NotionChatStatus) => void;
  setError: (error: string | null) => void;

  // Selectors
  getCurrentConversation: () => NotionChatConversation | null;
  getConversationMessages: (id: string) => NotionChatMessage[];
}

const generateId = () => crypto.randomUUID();

export const useNotionChatStore = create<NotionChatStore>()(
  subscribeWithSelector((set, get) => ({
    conversations: [],
    currentConversationId: null,
    isLoading: false,
    error: null,
    status: "idle",

    createConversation: () => {
      const id = generateId();
      const newConversation: NotionChatConversation = {
        id,
        messages: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };

      set((state) => ({
        conversations: [newConversation, ...state.conversations],
        currentConversationId: id,
      }));

      return id;
    },

    setCurrentConversation: (id) => {
      set({ currentConversationId: id });
    },

    addOrUpdateConversation: (conversation) => {
      set((state) => {
        const existingIndex = state.conversations.findIndex(
          (conv) => conv.id === conversation.id
        );

        if (existingIndex >= 0) {
          const newConversations = [...state.conversations];
          newConversations[existingIndex] = conversation;
          return { conversations: newConversations };
        } else {
          return {
            conversations: [conversation, ...state.conversations],
          };
        }
      });
    },

    addMessage: (conversationId, messageData) => {
      const messageId = generateId();

      let content = messageData.content;
      if (messageData.metadata?.eventType === "node_start") {
        const nodeName = messageData.metadata?.nodeName;
        if (nodeName === "reason") {
          content = "추론 중";
        } else if (nodeName === "act") {
          content = "작업 수행 중";
        } else if (nodeName === "observe") {
          content = "응답 검토 중";
        } else if (nodeName === "finalize") {
          content = "추론 완료";
        }
      }

      const message: NotionChatMessage = {
        ...messageData,
        content,
        id: messageId,
        timestamp: Date.now(),
      };

      set((state) => ({
        conversations: state.conversations.map((conv) =>
          conv.id === conversationId
            ? {
                ...conv,
                messages: [...conv.messages, message],
                updatedAt: Date.now(),
                title:
                  conv.title ||
                  (message.role === "user"
                    ? (typeof message.content === 'string'
                        ? message.content.slice(0, 50)
                        : message.content.data?.text?.slice(0, 50) || '')
                    : conv.title),
              }
            : conv
        ),
      }));

      return messageId;
    },

    updateMessage: (conversationId, messageId, updates) => {
      set((state) => ({
        conversations: state.conversations.map((conv) =>
          conv.id === conversationId
            ? {
                ...conv,
                messages: conv.messages.map((msg) =>
                  msg.id === messageId ? { ...msg, ...updates } : msg
                ),
                updatedAt: Date.now(),
              }
            : conv
        ),
      }));
    },

    appendMessageContent: (conversationId, messageId, content) => {
      set((state) => {
        return {
          conversations: state.conversations.map((conv) =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: conv.messages.map((msg) =>
                    msg.id === messageId
                      ? {
                          ...msg,
                          content:
                            typeof msg.content === 'string'
                              ? msg.content + content
                              : {
                                  ...msg.content,
                                  data: {
                                    ...msg.content.data,
                                    text: (msg.content.data?.text || '') + content
                                  }
                                }
                        }
                      : msg
                  ),
                  updatedAt: Date.now(),
                }
              : conv
          ),
        };
      });
    },

    deleteConversation: (id) => {
      set((state) => ({
        conversations: state.conversations.filter((conv) => conv.id !== id),
        currentConversationId:
          state.currentConversationId === id
            ? null
            : state.currentConversationId,
      }));
    },

    clearAllConversations: () => {
      set({
        conversations: [],
        currentConversationId: null,
      });
    },

    setStatus: (status) => {
      set({ status });
    },

    setError: (error) => {
      set({ error });
    },

    getCurrentConversation: () => {
      const { conversations, currentConversationId } = get();
      return (
        conversations.find((conv) => conv.id === currentConversationId) || null
      );
    },

    getConversationMessages: (id) => {
      const { conversations } = get();
      const conversation = conversations.find((conv) => conv.id === id);
      return conversation?.messages || [];
    },
  }))
);
