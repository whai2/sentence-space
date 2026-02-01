export type EventType =
  | "node_start"
  | "tool_start"
  | "tool_result"
  | "node_end"
  | "final"
  | "error"
  | "message_chunk"
  | "REASON_END";

export interface StreamEvent {
  event_type: EventType;
  node_name: string | null;
  iteration: number | null;
  data?: Record<string, any>;
  content?: string;
  timestamp?: number;
  is_final?: boolean;
}

export type StreamStatus = "idle" | "streaming" | "completed" | "error";

export interface StreamStats {
  nodeCount: number;
  toolCount: number;
  eventCount: number;
}
