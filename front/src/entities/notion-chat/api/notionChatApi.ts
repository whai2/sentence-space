/**
 * Notion 채팅 API 클라이언트 (비스트리밍)
 */

export interface NotionChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ToolExecutionDetail {
  tool_name: string;
  args: Record<string, any>;
  success: boolean;
  result_summary?: string | null;
  error?: string | null;
  iteration: number;
}

export interface NotionChatResponse {
  conversation_id: string;
  user_message: string;
  assistant_message: string;
  node_sequence: string[];
  execution_logs: Array<Record<string, any>>;
  used_tools: string[];
  tool_usage_count: number;
  tool_details: ToolExecutionDetail[];
}

export class NotionChatApi {
  private apiUrl: string;

  constructor() {
    const backendUrl = import.meta.env.VITE_BACKEND_URL;
    const apiVersion = import.meta.env.VITE_API_VERSION || "v1";

    if (backendUrl) {
      this.apiUrl = `${backendUrl}/api/${apiVersion}/notion/chat`;
    } else {
      this.apiUrl = "http://localhost:8000/api/v1/notion/chat";
    }
  }

  async sendMessage(request: NotionChatRequest): Promise<NotionChatResponse> {
    const response = await fetch(this.apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
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
