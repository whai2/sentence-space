/**
 * 채팅 관련 React Query 훅
 */

import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import type { ChatRequest, ChatResponse } from "./chatApi";
import { ChatApi } from "./chatApi";
import { SessionApi } from "./sessionApi";

// Query Keys
export const chatKeys = {
  all: ["chat"] as const,
  sessions: () => [...chatKeys.all, "sessions"] as const,
  session: (sessionId: string) => [...chatKeys.sessions(), sessionId] as const,
  sessionChats: (
    sessionId: string,
    options?: { limit?: number; skip?: number }
  ) => [...chatKeys.session(sessionId), "chats", options] as const,
};

// 세션 정보 조회 훅
export const useSession = (sessionId: string | null) => {
  const sessionApi = new SessionApi();

  return useQuery({
    queryKey: chatKeys.session(sessionId || ""),
    queryFn: () => sessionApi.getSession(sessionId!),
    enabled: !!sessionId,
  });
};

// 세션의 채팅 이력 조회 훅
export const useSessionChats = (
  sessionId: string | null,
  options?: { limit?: number; skip?: number }
) => {
  const sessionApi = new SessionApi();

  return useQuery({
    queryKey: chatKeys.sessionChats(sessionId || "", options),
    queryFn: () => sessionApi.getSessionChats(sessionId!, options),
    enabled: !!sessionId,
  });
};

// 모든 세션 목록 조회 훅
export const useAllSessions = (options?: { limit?: number; skip?: number }) => {
  const sessionApi = new SessionApi();

  return useQuery({
    queryKey: [...chatKeys.sessions(), options],
    queryFn: () => sessionApi.getAllSessions(options),
  });
};

// 모든 세션과 각 세션의 채팅 이력을 조회하는 훅
export const useAllSessionsWithChats = (options?: {
  limit?: number;
  skip?: number;
}) => {
  const sessionApi = new SessionApi();

  // 1단계: 세션 목록 조회
  const sessionsQuery = useQuery({
    queryKey: chatKeys.sessions(),
    queryFn: () => sessionApi.getAllSessions(),
  });

  // 2단계: 각 세션의 채팅 이력 조회
  const chatsQueries = useQueries({
    queries: sessionsQuery.data?.sessions
      ? sessionsQuery.data.sessions.map((session) => ({
          queryKey: chatKeys.sessionChats(session.session_id, options),
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
export const useSendChatMessage = () => {
  const queryClient = useQueryClient();
  const chatApi = new ChatApi();

  return useMutation({
    mutationFn: (request: ChatRequest) => chatApi.sendMessage(request),
    onSuccess: (data: ChatResponse) => {
      // 세션의 채팅 이력 쿼리 무효화하여 새로고침
      queryClient.invalidateQueries({
        queryKey: chatKeys.sessionChats(data.conversation_id),
      });
    },
  });
};
