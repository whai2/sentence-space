/**
 * Multi-Agent 관련 React Query 훅
 */

import { useQueries, useQuery } from "@tanstack/react-query";
import {
  MultiAgentSessionApi,
  type MultiAgentChatsResponse,
  type MultiAgentSessionsResponse,
} from "./multiAgentSessionApi";

// Query Keys
export const multiAgentKeys = {
  all: ["multi-agent"] as const,
  sessions: () => [...multiAgentKeys.all, "sessions"] as const,
  session: (sessionId: string) =>
    [...multiAgentKeys.sessions(), sessionId] as const,
  sessionChats: (
    sessionId: string,
    options?: { limit?: number; skip?: number }
  ) => [...multiAgentKeys.session(sessionId), "chats", options] as const,
};

// 모든 세션 목록 조회 훅
export const useMultiAgentSessions = (options?: {
  limit?: number;
  skip?: number;
}) => {
  const sessionApi = new MultiAgentSessionApi();

  return useQuery<MultiAgentSessionsResponse>({
    queryKey: [...multiAgentKeys.sessions(), options],
    queryFn: () => sessionApi.getAllSessions(options),
  });
};

// 세션의 채팅 목록 조회 훅
export const useMultiAgentSessionChats = (
  sessionId: string | null,
  options?: { limit?: number; skip?: number }
) => {
  const sessionApi = new MultiAgentSessionApi();

  return useQuery<MultiAgentChatsResponse>({
    queryKey: multiAgentKeys.sessionChats(sessionId || "", options),
    queryFn: () => sessionApi.getSessionChats(sessionId!, options),
    enabled: !!sessionId,
  });
};

// 모든 세션과 각 세션의 채팅 이력을 조회하는 훅
export const useMultiAgentSessionsWithChats = (options?: {
  limit?: number;
  skip?: number;
}) => {
  const sessionApi = new MultiAgentSessionApi();

  // 1단계: 세션 목록 조회
  const sessionsQuery = useQuery({
    queryKey: multiAgentKeys.sessions(),
    queryFn: () => sessionApi.getAllSessions(),
  });

  // 2단계: 각 세션의 채팅 이력 조회
  const chatsQueries = useQueries({
    queries: sessionsQuery.data?.sessions
      ? sessionsQuery.data.sessions.map((session) => ({
          queryKey: multiAgentKeys.sessionChats(session.session_id, options),
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
