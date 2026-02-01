import type { NotionChatMessage } from "@/entities/notion-chat";
import type { StreamEvent } from "@/shared/types/stream";
import { useCallback } from "react";
import { NotionChatStreamApi } from "../api/notionChatStreamApi";

interface UseNotionChatStreamOptions {
  onEvent?: (event: StreamEvent) => void;
  onMessage?: (message: NotionChatMessage) => string;
  onMessageUpdate?: (
    messageId: string,
    content: string,
    isStreaming?: boolean
  ) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

export const useNotionChatStream = () => {
  const streamChat = useCallback(
    async (
      message: string,
      conversationId: string | undefined,
      options: UseNotionChatStreamOptions = {}
    ) => {
      const { onEvent, onMessage, onMessageUpdate, onError, onComplete } =
        options;
      const streamApi = new NotionChatStreamApi();

      const nodeMessageMap = new Map<string, string>();
      const activeChunkMessageMap = new Map<string, string>();

      try {
        const request = {
          message: message.trim(),
          ...(conversationId && { conversation_id: conversationId }),
        };

        for await (const event of streamApi.streamChat(request)) {
          onEvent?.(event);

          if (event.event_type === "message_chunk") {
            const nodeName = event.node_name || "default";
            const chunkContent = event.data?.text || event.content || event.data?.content || "";

            if (!chunkContent) {
              continue;
            }

            const activeMessageId = activeChunkMessageMap.get(nodeName);

            if (activeMessageId) {
              onMessageUpdate?.(activeMessageId, chunkContent);
            } else {
              const newMessage: NotionChatMessage = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: chunkContent,
                timestamp: Date.now(),
                isStreaming: true,
                metadata: {
                  eventType: "message_chunk",
                  nodeName: event.node_name,
                },
              };
              const actualMessageId = onMessage?.(newMessage);

              if (actualMessageId) {
                activeChunkMessageMap.set(nodeName, actualMessageId);
              }
            }
            continue;
          }

          const result = convertEventToMessage(event, nodeMessageMap, activeChunkMessageMap);
          if (result) {
            if (result.type === "new") {
              const actualMessageId = onMessage?.(result.message);

              if (actualMessageId && result.message.metadata?.nodeName) {
                nodeMessageMap.set(
                  result.message.metadata.nodeName,
                  actualMessageId
                );
              }
            } else if (result.type === "update") {
              onMessageUpdate?.(
                result.messageId,
                result.content,
                result.isStreaming
              );
            }
          }
        }

        onComplete?.();
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));
        onError?.(err);

        const errorMessage: NotionChatMessage = {
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

type ConvertResult =
  | { type: "new"; message: NotionChatMessage }
  | {
      type: "update";
      messageId: string;
      content: string;
      isStreaming?: boolean;
    }
  | null;

function convertEventToMessage(
  event: StreamEvent,
  nodeMessageMap: Map<string, string>,
  chunkMessageMap: Map<string, string>
): ConvertResult {
  const messageId = crypto.randomUUID();
  const timestamp = Date.now();

  switch (event.event_type) {
    case "final": {
      const data = event.data || {};
      const executionLogs = data.execution_logs || [];
      const nodeSequence = data.node_sequence || [];
      const usedTools = data.used_tools || [];
      const toolUsageCount = data.tool_usage_count || 0;

      let logContent = "📊 실행 완료\n\n";
      logContent += `**실행된 노드**: ${nodeSequence.join(" → ")}\n\n`;

      if (executionLogs.length > 0) {
        logContent += "**실행 로그**:\n";
        executionLogs.forEach((log: any) => {
          logContent += `- ${log.node} (반복: ${log.iteration})`;
          if (log.has_tool_calls) {
            logContent += " - 도구 사용됨";
          }
          if (log.is_final) {
            logContent += " - 최종";
          }
          logContent += "\n";
        });
        logContent += "\n";
      }

      if (toolUsageCount > 0) {
        logContent += `**사용된 도구 수**: ${toolUsageCount}\n`;
        if (usedTools.length > 0) {
          logContent += `**도구 목록**: ${usedTools.join(", ")}\n`;
        }
      }

      return {
        type: "new",
        message: {
          id: messageId,
          role: "assistant",
          content: logContent,
          timestamp,
          isStreaming: false,
          metadata: {
            eventType: "final",
            nodeName: event.node_name,
            iteration: event.iteration,
            isCollapsible: true,
          },
        },
      };
    }

    case "node_start": {
      const streamingMessage: NotionChatMessage = {
        id: messageId,
        role: "assistant",
        content: "",
        timestamp,
        isStreaming: true,
        metadata: {
          eventType: "node_start",
          nodeName: event.node_name,
          iteration: event.iteration,
        },
      };

      if (event.node_name) {
        nodeMessageMap.set(event.node_name, messageId);
      }

      return {
        type: "new",
        message: streamingMessage,
      };
    }

    case "tool_result": {
      const toolResult = formatToolResult(event.data || {});
      return {
        type: "new",
        message: {
          id: messageId,
          role: "assistant",
          content: `🔧 도구 실행 결과:\n${toolResult}`,
          timestamp,
          isStreaming: true,
          metadata: {
            eventType: "tool_result",
            nodeName: event.node_name,
            iteration: event.iteration,
          },
        },
      };
    }

    case "node_end":
    case "REASON_END": {
      const nodeName = event.node_name || "default";
      const activeMessageId = chunkMessageMap.get(nodeName);

      if (activeMessageId) {
        chunkMessageMap.delete(nodeName);

        return {
          type: "update",
          messageId: activeMessageId,
          content: "",
          isStreaming: false,
        };
      }
      return null;
    }

    case "error": {
      const errorContent = event.data?.error
        ? String(event.data.error)
        : "알 수 없는 에러가 발생했습니다.";
      return {
        type: "new",
        message: {
          id: messageId,
          role: "assistant",
          content: `❌ 에러: ${errorContent}`,
          timestamp,
          isStreaming: false,
          metadata: {
            eventType: "error",
            nodeName: event.node_name,
            iteration: event.iteration,
          },
        },
      };
    }

    case "message_chunk":
      return null;

    default:
      return null;
  }
}

function formatToolResult(data: Record<string, any>): string {
  if (!data || typeof data !== "object") {
    return "결과 없음";
  }

  if (typeof data === "string") {
    return data;
  }

  try {
    const jsonString = JSON.stringify(data, null, 2);
    if (jsonString.length > 500) {
      return jsonString.slice(0, 500) + "\n... (생략)";
    }
    return jsonString;
  } catch {
    return String(data);
  }
}
