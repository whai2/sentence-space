/**
 * Multi-Agent 채팅 인터페이스 컴포넌트
 */

import type { ChatMessage } from "@/entities/chat";
import { useEffect, useMemo, useRef, useState } from "react";
import { useChatStore } from "../../shared/store/chatStore";
import { ChatInput, MessagesArea } from "../../shared/ui";
import { MessageDisplay } from "../chat/MessageDisplay";
import { useMultiAgentSessionChats } from "./api";
import { useMultiAgentStream } from "./hooks";

export const MultiAgentChatInterface = () => {
  const [inputValue, setInputValue] = useState("");
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    getCurrentConversation,
    addMessage,
    updateMessage,
    appendMessageContent,
    status,
    setStatus,
  } = useChatStore();

  const { streamChat } = useMultiAgentStream();
  const currentConversation = getCurrentConversation();

  // 세션 채팅 이력 조회 (리액트 쿼리)
  const { data: sessionChatsData, isLoading: isLoadingHistory } =
    useMultiAgentSessionChats(currentConversation?.id || null, { limit: 100 });

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
            nodeName: chat.node_sequence?.join(" → ") || null,
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
    setCurrentAgent(null);

    // 사용자 메시지 추가
    addMessage(currentConversation.id, {
      role: "user",
      content: messageText,
    });

    setStatus("streaming");

    // Multi-Agent 스트림 시작
    await streamChat(messageText, currentConversation.id, {
      onMessage: (message: ChatMessage) => {
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
      onAgentChange: (agent: string) => {
        setCurrentAgent(agent);
      },
      onError: () => {
        setStatus("error");
        setCurrentAgent(null);
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
        setCurrentAgent(null);
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
          <MessageDisplay key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </MessagesArea>
      <div style={{ padding: "20px" }}>
        {currentAgent && (
          <div
            style={{
              marginBottom: "8px",
              fontSize: "12px",
              color: "#666",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: "#4CAF50",
                animation: "pulse 1.5s infinite",
              }}
            />
            {getAgentDisplayName(currentAgent)} 에이전트 실행 중...
          </div>
        )}
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSubmit={handleSubmit}
          disabled={isDisabled}
          placeholder={
            isDisabled
              ? "AI가 응답 중입니다..."
              : "Notion, ClickUp에 대해 물어보세요..."
          }
        />
      </div>
    </>
  );
};

function getAgentDisplayName(agentName: string): string {
  const displayNames: Record<string, string> = {
    supervisor: "감독자",
    notion_agent: "Notion",
    clickup_reader: "ClickUp 조회",
    clickup_writer: "ClickUp 작업",
  };
  return displayNames[agentName] || agentName;
}
