import type { NotionChatMessage } from "@/entities/notion-chat";
import { useNotionSessionChats } from "@/entities/notion-chat";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNotionChatStore } from "../../shared/store/notionChatStore";
import { ChatInput, MessagesArea } from "../../shared/ui";
import { useNotionChatStream } from "../notion-chat-stream";
import { NotionMessageDisplay } from "./NotionMessageDisplay";

export const NotionChatInterface = () => {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    getCurrentConversation,
    addMessage,
    updateMessage,
    appendMessageContent,
    status,
    setStatus,
  } = useNotionChatStore();

  const { streamChat } = useNotionChatStream();
  const currentConversation = getCurrentConversation();

  const {
    data: sessionChatsData,
    isLoading: isLoadingHistory,
  } = useNotionSessionChats(currentConversation?.id || null, { limit: 100 });

  const sessionMessages = useMemo<NotionChatMessage[]>(() => {
    if (!sessionChatsData?.chats) return [];

    return sessionChatsData.chats.flatMap((chat) => {
      const timestamp = new Date(chat.created_at).getTime();
      let assistantContent = chat.assistant_message;
      if (chat.tool_details && chat.tool_details.length > 0) {
        assistantContent +=
          "\n\n**사용된 도구**: " + chat.used_tools.join(", ");
      }

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
          content: assistantContent,
          timestamp: timestamp + 1,
          isStreaming: false,
          metadata: {
            eventType: "final",
            nodeName: null,
            iteration: null,
          },
        },
      ];
    });
  }, [sessionChatsData]);

  const streamingMessages = useMemo(
    () => currentConversation?.messages || [],
    [currentConversation?.messages]
  );

  const messages = useMemo(() => {
    const sessionMessageIds = new Set(sessionMessages.map((m) => m.id));
    const newStreamingMessages = streamingMessages.filter(
      (m) => !sessionMessageIds.has(m.id)
    );
    return [...sessionMessages, ...newStreamingMessages];
  }, [sessionMessages, streamingMessages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async () => {
    if (!inputValue.trim() || !currentConversation) return;

    const messageText = inputValue.trim();
    setInputValue("");
    setStatus("sending");

    addMessage(currentConversation.id, {
      role: "user",
      content: messageText,
    });

    setStatus("streaming");

    await streamChat(messageText, currentConversation.id, {
      onMessage: (message: NotionChatMessage) => {
        const messageId = addMessage(currentConversation.id, {
          role: message.role,
          content: message.content,
          isStreaming: message.isStreaming,
          metadata: message.metadata,
        });
        return messageId;
      },
      onMessageUpdate: (
        messageId: string,
        chunkContent: string,
        isStreaming?: boolean
      ) => {
        if (!currentConversation) return;

        if (chunkContent) {
          appendMessageContent(currentConversation.id, messageId, chunkContent);
        }

        if (isStreaming !== undefined) {
          updateMessage(currentConversation.id, messageId, { isStreaming });
        }
      },
      onError: () => {
        setStatus("error");
      },
      onComplete: () => {
        const conversation = getCurrentConversation();
        if (conversation) {
          conversation.messages.forEach((msg) => {
            if (msg.isStreaming) {
              updateMessage(currentConversation.id, msg.id, {
                isStreaming: false,
              });
            }
          });
        }
        setStatus("completed");
      },
    });
  };

  const isDisabled = status === "sending" || status === "streaming";

  if (!currentConversation) {
    return (
      <MessagesArea>
        <div
          style={{
            textAlign: "center",
            color: "#666",
            marginTop: "50px",
            fontSize: "18px",
          }}
        >
          대화를 선택하거나 새 대화를 시작하세요
        </div>
      </MessagesArea>
    );
  }

  if (isLoadingHistory) {
    return (
      <MessagesArea>
        <div
          style={{
            textAlign: "center",
            color: "#666",
            marginTop: "50px",
            fontSize: "18px",
          }}
        >
          채팅 이력을 불러오는 중...
        </div>
      </MessagesArea>
    );
  }

  return (
    <>
      <MessagesArea>
        {messages.map((message) => (
          <NotionMessageDisplay key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </MessagesArea>
      <div style={{ padding: "20px" }}>
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          disabled={isDisabled}
          placeholder={
            isDisabled ? "AI가 응답 중입니다..." : "Notion에 대해 물어보세요..."
          }
        />
      </div>
    </>
  );
};
