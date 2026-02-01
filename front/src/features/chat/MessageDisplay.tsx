import type { ChatMessage } from "@/entities/chat";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Avatar,
  MessageBubble,
  MessageContainer,
  MessageTime,
  TypingIndicator,
} from "../../shared/ui";

interface MessageDisplayProps {
  message: ChatMessage;
}

const formatTime = (timestamp: number) => {
  return new Date(timestamp).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const MessageDisplay = ({ message }: MessageDisplayProps) => {
  const [isExpanded, setIsExpanded] = useState(true);

  // content를 문자열로 변환
  const contentString = typeof message.content === 'string'
    ? message.content
    : (message.content.data?.text || '');

  const isCollapsible = message.metadata?.isCollapsible;

  return (
    <MessageContainer role={message.role} isStreaming={message.isStreaming}>
      <Avatar role={message.role}>
        {message.role === "user" ? "U" : "AI"}
      </Avatar>
      <div style={{ flex: 1 }}>
        <MessageBubble role={message.role}>
          {message.isStreaming && contentString === "" ? (
            <TypingIndicator>
              <span />
              <span />
              <span />
            </TypingIndicator>
          ) : isCollapsible ? (
            <div>
              <div
                onClick={() => setIsExpanded(!isExpanded)}
                style={{
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  userSelect: "none",
                }}
              >
                <span style={{ fontSize: "14px" }}>
                  {isExpanded ? "▼" : "▶"}
                </span>
                <strong>에이전트 기록</strong>
              </div>
              {isExpanded && (
                <div style={{ marginTop: "12px", paddingTop: "12px", borderTop: "1px solid rgba(0, 0, 0, 0.1)" }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {contentString}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {contentString}
            </ReactMarkdown>
          )}
        </MessageBubble>
        <MessageTime>{formatTime(message.timestamp)}</MessageTime>
      </div>
    </MessageContainer>
  );
};
