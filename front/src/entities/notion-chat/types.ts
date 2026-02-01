export interface NotionChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string | { event_type?: string; node_name?: string; data?: { text?: string }; timestamp?: number };
  timestamp: number;
  isStreaming?: boolean;
  metadata?: {
    eventType?: string;
    nodeName?: string | null;
    iteration?: number | null;
    isCollapsible?: boolean;
  };
}

export interface NotionChatConversation {
  id: string;
  title?: string;
  messages: NotionChatMessage[];
  createdAt: number;
  updatedAt: number;
}

export interface NotionChatState {
  conversations: NotionChatConversation[];
  currentConversationId: string | null;
  isLoading: boolean;
  error: string | null;
}

export type NotionChatStatus =
  | "idle"
  | "sending"
  | "streaming"
  | "error"
  | "completed";
