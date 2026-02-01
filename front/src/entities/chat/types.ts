export interface ChatMessage {
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

export interface ChatConversation {
  id: string;
  title?: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

export interface ChatState {
  conversations: ChatConversation[];
  currentConversationId: string | null;
  isLoading: boolean;
  error: string | null;
}

export type ChatStatus =
  | "idle"
  | "sending"
  | "streaming"
  | "error"
  | "completed";
