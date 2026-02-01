/**
 * Multi-Agent 스트리밍 채팅 훅
 * ClickUp Demo와 동일한 이벤트 형식 사용
 */

import type { ChatMessage } from "@/entities/chat";
import type { StreamEvent } from "@/shared/types/stream";
import { useCallback } from "react";
import { MultiAgentStreamApi } from "../api/multiAgentStreamApi";

interface UseMultiAgentStreamOptions {
  onEvent?: (event: StreamEvent) => void;
  onMessage?: (message: ChatMessage) => string;
  onMessageUpdate?: (
    messageId: string,
    content: string,
    isStreaming?: boolean
  ) => void;
  onAgentChange?: (agent: string) => void;
  onError?: (error: Error) => void;
  onComplete?: (conversationId: string) => void;
}

export const useMultiAgentStream = () => {
  const streamChat = useCallback(
    async (
      message: string,
      conversationId: string | undefined,
      options: UseMultiAgentStreamOptions = {}
    ) => {
      const {
        onEvent,
        onMessage,
        onMessageUpdate,
        onAgentChange,
        onError,
        onComplete,
      } = options;

      const streamApi = new MultiAgentStreamApi();
      let currentMessageId: string | null = null;
      let finalConversationId = conversationId || "";
      const activeChunkMessageMap = new Map<string, string>();

      try {
        const request = {
          message: message.trim(),
          ...(conversationId && { conversation_id: conversationId }),
        };

        for await (const rawEvent of streamApi.streamChat(request)) {
          const event = rawEvent as StreamEvent;
          if (!event || !event.event_type) continue;

          onEvent?.(event);

          switch (event.event_type) {
            case "node_start": {
              // 에이전트 노드 시작
              const nodeName = event.node_name || "unknown";
              onAgentChange?.(nodeName);

              // 노드 시작 알림 메시지
              const nodeMessage: ChatMessage = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: `🤖 ${getAgentDisplayName(nodeName)} 실행 중...`,
                timestamp: Date.now(),
                isStreaming: true,
                metadata: {
                  eventType: "node_start",
                  nodeName: nodeName,
                  iteration: event.iteration,
                  isCollapsible: true,
                },
              };
              const nodeMessageId = onMessage?.(nodeMessage);
              if (nodeMessageId && nodeName) {
                activeChunkMessageMap.set(nodeName, nodeMessageId);
              }
              break;
            }

            case "message_chunk": {
              // LLM 스트리밍 토큰
              const nodeName = event.node_name || "supervisor";
              const chunkText = event.data?.text || "";
              if (!chunkText) continue;

              const activeMessageId = activeChunkMessageMap.get(nodeName);

              if (activeMessageId) {
                // 기존 메시지에 누적
                onMessageUpdate?.(activeMessageId, chunkText);
              } else if (currentMessageId) {
                // fallback: 현재 메시지에 누적
                onMessageUpdate?.(currentMessageId, chunkText);
              } else {
                // 새 메시지 생성
                const newMessage: ChatMessage = {
                  id: crypto.randomUUID(),
                  role: "assistant",
                  content: chunkText,
                  timestamp: Date.now(),
                  isStreaming: true,
                  metadata: {
                    eventType: "message_chunk",
                    nodeName: nodeName,
                  },
                };
                const actualId = onMessage?.(newMessage);
                if (actualId) {
                  currentMessageId = actualId;
                  activeChunkMessageMap.set(nodeName, actualId);
                }
              }
              break;
            }

            case "tool_start": {
              // 도구 호출 시작
              const toolName = event.data?.tool_name || "unknown";
              const toolMessage: ChatMessage = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: `🔧 도구 호출: ${toolName}`,
                timestamp: Date.now(),
                isStreaming: true,
                metadata: {
                  eventType: "tool_start",
                  nodeName: event.node_name,
                  iteration: event.iteration,
                  isCollapsible: true,
                },
              };
              onMessage?.(toolMessage);
              break;
            }

            case "tool_result": {
              // 도구 실행 결과
              const toolName = event.data?.tool_name || "unknown";
              const success = event.data?.success ?? true;
              const result = event.data?.result || "";
              const resultSummary = typeof result === "string"
                ? result.slice(0, 200)
                : JSON.stringify(result).slice(0, 200);

              const toolResultMessage: ChatMessage = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: success
                  ? `✅ ${toolName} 완료\n${resultSummary}${resultSummary.length >= 200 ? "..." : ""}`
                  : `❌ ${toolName} 실패: ${event.data?.error || "알 수 없는 에러"}`,
                timestamp: Date.now(),
                isStreaming: false,
                metadata: {
                  eventType: "tool_result",
                  nodeName: event.node_name,
                  iteration: event.iteration,
                  isCollapsible: true,
                },
              };
              onMessage?.(toolResultMessage);
              break;
            }

            case "node_end": {
              // 노드 종료 - 활성 메시지 스트리밍 종료
              const nodeName = event.node_name || "default";
              const activeMessageId = activeChunkMessageMap.get(nodeName);
              if (activeMessageId) {
                onMessageUpdate?.(activeMessageId, "", false);
                activeChunkMessageMap.delete(nodeName);
              }
              break;
            }

            case "final": {
              // 최종 결과
              finalConversationId = event.data?.conversation_id || finalConversationId;
              const nodeSequence = event.data?.node_sequence || [];
              const usedTools = event.data?.used_tools || [];
              const toolUsageCount = event.data?.tool_usage_count || 0;

              // 모든 스트리밍 메시지 종료
              activeChunkMessageMap.forEach((msgId) => {
                onMessageUpdate?.(msgId, "", false);
              });
              activeChunkMessageMap.clear();

              if (currentMessageId) {
                onMessageUpdate?.(currentMessageId, "", false);
              }

              // 최종 요약 메시지
              let summaryContent = "📊 실행 완료\n\n";
              summaryContent += `**에이전트 경로**: ${nodeSequence.join(" → ") || "없음"}\n`;
              if (toolUsageCount > 0) {
                summaryContent += `**사용된 도구**: ${usedTools.join(", ")}\n`;
                summaryContent += `**도구 호출 횟수**: ${toolUsageCount}\n`;
              }

              const summaryMessage: ChatMessage = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: summaryContent,
                timestamp: Date.now(),
                isStreaming: false,
                metadata: {
                  eventType: "final",
                  nodeName: event.node_name,
                  iteration: event.iteration,
                  isCollapsible: true,
                },
              };
              onMessage?.(summaryMessage);
              break;
            }

            case "error": {
              // 에러
              const errorContent = event.data?.error || "알 수 없는 에러";
              const errorMessage: ChatMessage = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: `❌ 에러: ${errorContent}`,
                timestamp: Date.now(),
                isStreaming: false,
                metadata: {
                  eventType: "error",
                  nodeName: event.node_name,
                  iteration: event.iteration,
                },
              };
              onMessage?.(errorMessage);
              break;
            }
          }
        }

        onComplete?.(finalConversationId);
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));
        onError?.(err);

        const errorMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `에러 발생: ${err.message}`,
          timestamp: Date.now(),
          isStreaming: false,
          metadata: {
            eventType: "error",
          },
        };
        onMessage?.(errorMessage);
      }
    },
    []
  );

  return { streamChat };
};

/**
 * 에이전트 이름을 사용자 친화적으로 변환
 */
function getAgentDisplayName(agentName: string): string {
  const displayNames: Record<string, string> = {
    supervisor: "감독자 (Supervisor)",
    notion_agent: "Notion 에이전트",
    clickup_reader: "ClickUp 조회 에이전트",
    clickup_writer: "ClickUp 작업 에이전트",
  };
  return displayNames[agentName] || agentName;
}
