import type { StreamRequest } from "@/shared/api/streamApi";
import { StreamApi } from "@/shared/api/streamApi";

export class NotionChatStreamApi {
  private streamApi: StreamApi;

  constructor() {
    const apiUrl = this.getStreamApiUrl();
    this.streamApi = new StreamApi(apiUrl);
  }

  private getStreamApiUrl(): string {
    const backendUrl = import.meta.env.VITE_BACKEND_URL;
    const apiVersion = import.meta.env.VITE_API_VERSION || "v1";

    if (backendUrl) {
      return `${backendUrl}/api/${apiVersion}/notion/chat/stream`;
    }

    return "http://localhost:8000/api/v1/notion/chat/stream";
  }

  async *streamChat(request: StreamRequest) {
    yield* this.streamApi.streamChat(request);
  }
}
