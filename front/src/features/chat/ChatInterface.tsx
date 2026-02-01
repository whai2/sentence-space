import type { ChatMessage } from "@/entities/chat";
import { useSessionChats } from "@/entities/chat";
import { useEffect, useMemo, useRef, useState } from "react";
import { useChatStore } from "../../shared/store/chatStore";
import { ChatInput, MessagesArea } from "../../shared/ui";
import { useChatStream } from "../chat-stream";
import { MessageDisplay } from "./MessageDisplay";

export const ChatInterface = () => {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    getCurrentConversation,
    addMessage,
    updateMessage,
    appendMessageContent,
    status,
    setStatus,
  } = useChatStore();

  const { streamChat } = useChatStream();
  const currentConversation = getCurrentConversation();

  // 세션 채팅 이력 조회 (리액트 쿼리)
  const {
    data: sessionChatsData,
    isLoading: isLoadingHistory,
  } = useSessionChats(currentConversation?.id || null, { limit: 100 });

  // 세션 채팅 이력을 ChatMessage 배열로 변환
  const sessionMessages = useMemo<ChatMessage[]>(() => {
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

  // 스트리밍 중인 메시지 (로컬 상태에만 있는 메시지)
  const streamingMessages = useMemo(
    () => currentConversation?.messages || [],
    [currentConversation?.messages]
  );

  // 세션 메시지와 스트리밍 메시지를 병합
  // 스트리밍 메시지는 세션 메시지보다 최신이므로 뒤에 추가
  const messages = useMemo(() => {
    const sessionMessageIds = new Set(sessionMessages.map((m) => m.id));
    // 세션에 없는 메시지만 스트리밍 메시지로 추가 (새로 입력 중인 메시지)
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

    // 사용자 메시지 추가
    addMessage(currentConversation.id, {
      role: "user",
      content: messageText,
    });

    setStatus("streaming");

    // 스트림 시작
    await streamChat(messageText, currentConversation.id, {
      onMessage: (message: ChatMessage) => {
        // 새 메시지 추가하고 실제 생성된 messageId 반환
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
        // 기존 메시지의 content에 chunk 누적 또는 isStreaming 업데이트
        if (!currentConversation) return;

        // chunkContent가 있으면 누적
        if (chunkContent) {
          appendMessageContent(currentConversation.id, messageId, chunkContent);
        }

        // isStreaming 상태 업데이트
        if (isStreaming !== undefined) {
          updateMessage(currentConversation.id, messageId, { isStreaming });
        }
      },
      onError: () => {
        setStatus("error");
      },
      onComplete: () => {
        // 모든 스트리밍 메시지의 isStreaming을 false로 변경
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

  // 에러가 발생해도 계속 진행 (세션이 없을 수도 있음)

  return (
    <>
      <MessagesArea>
        {messages.map((message) => (
          <MessageDisplay key={message.id} message={message} />
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
            isDisabled ? "AI가 응답 중입니다..." : "메시지를 입력하세요..."
          }
        />
      </div>
    </>
  );
};
