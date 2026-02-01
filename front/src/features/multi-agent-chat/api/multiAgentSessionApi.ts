/**
 * Multi-Agent 세션 API 클라이언트
 */

export interface MultiAgentChatHistory {
  user_message: string;
  assistant_message: string;
  agent_path: string[];
  created_at: string;
}

export interface MultiAgentHistoryResponse {
  session_id: string;
  history: MultiAgentChatHistory[];
}

export interface MultiAgentSessionInfo {
  session_id: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MultiAgentSessionsResponse {
  sessions: MultiAgentSessionInfo[];
  total: number;
}

export interface MultiAgentChatDetail {
  id: string;
  session_id: string;
  user_message: string;
  assistant_message: string;
  node_sequence: string[];
  execution_logs: Array<Record<string, unknown>>;
  used_tools: string[];
  tool_usage_count: number;
  tool_details: Array<{
    tool_name: string;
    args: Record<string, unknown>;
    success: boolean;
    result_summary?: string | null;
    error?: string | null;
    iteration: number;
  }>;
  created_at: string;
}

export interface MultiAgentChatsResponse {
  chats: MultiAgentChatDetail[];
  total: number;
}

export class MultiAgentSessionApi {
  private baseUrl: string;

  constructor() {
    const backendUrl = import.meta.env.VITE_BACKEND_URL;
    const apiVersion = import.meta.env.VITE_API_VERSION || "v1";

    if (backendUrl) {
      this.baseUrl = `${backendUrl}/api/${apiVersion}/multi-agent`;
    } else {
      this.baseUrl = "http://localhost:8000/api/v1/multi-agent";
    }
  }

  /**
   * 모든 세션 목록 조회
   */
  async getAllSessions(options?: {
    limit?: number;
    skip?: number;
  }): Promise<MultiAgentSessionsResponse> {
    const params = new URLSearchParams();
    if (options?.limit) {
      params.append("limit", options.limit.toString());
    }
    if (options?.skip) {
      params.append("skip", options.skip.toString());
    }

    const queryString = params.toString();
    const url = `${this.baseUrl}/sessions${queryString ? `?${queryString}` : ""}`;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `HTTP error! status: ${response.status}, message: ${errorText}`
      );
    }

    return response.json();
  }

  /**
   * 세션의 채팅 이력 조회
   */
  async getSessionHistory(
    sessionId: string,
    limit: number = 50
  ): Promise<MultiAgentHistoryResponse> {
    const url = `${this.baseUrl}/sessions/${sessionId}/history?limit=${limit}`;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.status === 404) {
      return { session_id: sessionId, history: [] };
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `HTTP error! status: ${response.status}, message: ${errorText}`
      );
    }

    return response.json();
  }

  /**
   * 세션의 채팅 목록 조회 (ChatPage와 동일한 형식)
   */
  async getSessionChats(
    sessionId: string,
    options?: { limit?: number; skip?: number }
  ): Promise<MultiAgentChatsResponse> {
    const params = new URLSearchParams();
    if (options?.limit) {
      params.append("limit", options.limit.toString());
    }
    if (options?.skip) {
      params.append("skip", options.skip.toString());
    }

    const queryString = params.toString();
    const url = `${this.baseUrl}/sessions/${sessionId}/chats${
      queryString ? `?${queryString}` : ""
    }`;

    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.status === 404) {
      return { chats: [], total: 0 };
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `HTTP error! status: ${response.status}, message: ${errorText}`
      );
    }

    return response.json();
  }
}
