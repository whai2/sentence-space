/**
 * Notion 세션 및 채팅 이력 조회 API 클라이언트
 */

export interface NotionSessionInfo {
  session_id: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface NotionChatHistory {
  id: string;
  session_id: string;
  user_message: string;
  assistant_message: string;
  node_sequence: string[];
  execution_logs: Array<Record<string, any>>;
  used_tools: string[];
  tool_usage_count: number;
  tool_details: Array<{
    tool_name: string;
    args: Record<string, any>;
    success: boolean;
    result_summary?: string | null;
    error?: string | null;
    iteration: number;
  }>;
  created_at: string;
}

export interface NotionSessionChatsResponse {
  chats: NotionChatHistory[];
  total: number;
}

export interface NotionSessionsResponse {
  sessions: NotionSessionInfo[];
  total: number;
}

export class NotionSessionApi {
  private baseUrl: string;

  constructor() {
    const backendUrl = import.meta.env.VITE_BACKEND_URL;
    const apiVersion = import.meta.env.VITE_API_VERSION || "v1";

    if (backendUrl) {
      this.baseUrl = `${backendUrl}/api/${apiVersion}/notion`;
    } else {
      this.baseUrl = "http://localhost:8000/api/v1/notion";
    }
  }

  /**
   * 세션 정보 조회
   */
  async getSession(sessionId: string): Promise<NotionSessionInfo | null> {
    const response = await fetch(`${this.baseUrl}/sessions/${sessionId}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (response.status === 404) {
      return null;
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
   * 세션의 채팅 이력 조회
   */
  async getSessionChats(
    sessionId: string,
    options?: { limit?: number; skip?: number }
  ): Promise<NotionSessionChatsResponse> {
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

    const data = await response.json();
    return data;
  }

  /**
   * 모든 세션 목록 조회 (페이지네이션 지원)
   */
  async getAllSessions(options?: {
    limit?: number;
    skip?: number;
  }): Promise<NotionSessionsResponse> {
    const params = new URLSearchParams();
    if (options?.limit) {
      params.append("limit", options.limit.toString());
    }
    if (options?.skip) {
      params.append("skip", options.skip.toString());
    }

    const queryString = params.toString();
    const url = `${this.baseUrl}/sessions${
      queryString ? `?${queryString}` : ""
    }`;

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
}
