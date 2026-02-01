import type { GraphData, NodeDetail } from "../types";

export class KnowledgeGraphApi {
  private baseUrl: string;

  constructor() {
    const backendUrl = import.meta.env.VITE_BACKEND_URL;
    const apiVersion = import.meta.env.VITE_API_VERSION || "v1";

    if (backendUrl) {
      this.baseUrl = `${backendUrl}/api/${apiVersion}/multi-agent/knowledge-graph`;
    } else {
      this.baseUrl = "http://localhost:8000/api/v1/multi-agent/knowledge-graph";
    }
  }

  async getGraph(): Promise<GraphData> {
    const response = await fetch(`${this.baseUrl}/graph`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch graph: ${response.statusText}`);
    }

    return response.json();
  }

  async getNodeDetail(nodeId: string): Promise<NodeDetail> {
    const encoded = encodeURIComponent(nodeId);
    const response = await fetch(`${this.baseUrl}/nodes/${encoded}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch node: ${response.statusText}`);
    }

    return response.json();
  }
}
