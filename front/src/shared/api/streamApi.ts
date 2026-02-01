import type { StreamEvent } from '../types/stream';

export interface StreamRequest {
  message: string;
  conversation_id?: string;
}

export class StreamApi {
  private apiUrl: string;

  constructor(apiUrl: string) {
    this.apiUrl = apiUrl;
  }

  async *streamChat(request: StreamRequest): AsyncGenerator<StreamEvent> {
    const response = await fetch(this.apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              return;
            }

            try {
              const event = JSON.parse(data);
              yield event;
            } catch (e) {
              console.error('JSON parsing error:', e, data);
              yield {
                event_type: 'error',
                node_name: null,
                iteration: null,
                data: { error: `JSON parsing failed: ${(e as Error).message}`, raw: data },
                timestamp: Date.now() / 1000,
              } as StreamEvent;
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
}
