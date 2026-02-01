/**
 * Notion 채팅 관련 React Query 훅
 */

import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { NotionChatRequest, NotionChatResponse } from "./notionChatApi";
import { NotionChatApi } from "./notionChatApi";
import { NotionSessionApi } from "./notionSessionApi";

// Query Keys
export const notionChatKeys = {
  all: ["notion-chat"] as const,
  sessions: () => [...notionChatKeys.all, "sessions"] as const,
  session: (sessionId: string) => [...notionChatKeys.sessions(), sessionId] as const,
  sessionChats: (
    sessionId: string,
    options?: { limit?: number; skip?: number }
  ) => [...notionChatKeys.session(sessionId), "chats", options] as const,
};

// 세션 정보 조회 훅
export const useNotionSession = (sessionId: string | null) => {
  const sessionApi = new NotionSessionApi();

  return useQuery({
    queryKey: notionChatKeys.session(sessionId || ""),
    queryFn: () => sessionApi.getSession(sessionId!),
    enabled: !!sessionId,
  });
};

// 세션의 채팅 이력 조회 훅
export const useNotionSessionChats = (
  sessionId: string | null,
  options?: { limit?: number; skip?: number }
) => {
  const sessionApi = new NotionSessionApi();

  return useQuery({
    queryKey: notionChatKeys.sessionChats(sessionId || "", options),
    queryFn: () => sessionApi.getSessionChats(sessionId!, options),
    enabled: !!sessionId,
  });
};

// 모든 세션 목록 조회 훅
export const useAllNotionSessions = (options?: { limit?: number; skip?: number }) => {
  const sessionApi = new NotionSessionApi();

  return useQuery({
    queryKey: [...notionChatKeys.sessions(), options],
    queryFn: () => sessionApi.getAllSessions(options),
  });
};

// 모든 세션과 각 세션의 채팅 이력을 조회하는 훅
export const useAllNotionSessionsWithChats = (options?: {
  limit?: number;
  skip?: number;
}) => {
  const sessionApi = new NotionSessionApi();

  const sessionsQuery = useQuery({
    queryKey: notionChatKeys.sessions(),
    queryFn: () => sessionApi.getAllSessions(),
  });

  const chatsQueries = useQueries({
    queries: sessionsQuery.data?.sessions
      ? sessionsQuery.data.sessions.map((session) => ({
          queryKey: notionChatKeys.sessionChats(session.session_id, options),
          queryFn: () =>
            sessionApi.getSessionChats(session.session_id, options),
          enabled:
            !!sessionsQuery.data && sessionsQuery.data.sessions.length > 0,
        }))
      : [],
  });

  return {
    sessions: sessionsQuery.data?.sessions || [],
    chats: chatsQueries.map((query) => query.data).filter(Boolean),
    isLoading:
      sessionsQuery.isLoading || chatsQueries.some((query) => query.isLoading),
    isError:
      sessionsQuery.isError || chatsQueries.some((query) => query.isError),
    error:
      sessionsQuery.error || chatsQueries.find((query) => query.error)?.error,
  };
};

// 채팅 메시지 전송 Mutation 훅
export const useSendNotionChatMessage = () => {
  const queryClient = useQueryClient();
  const chatApi = new NotionChatApi();

  return useMutation({
    mutationFn: (request: NotionChatRequest) => chatApi.sendMessage(request),
    onSuccess: (data: NotionChatResponse) => {
      queryClient.invalidateQueries({
        queryKey: notionChatKeys.sessionChats(data.conversation_id),
      });
    },
  });
};
