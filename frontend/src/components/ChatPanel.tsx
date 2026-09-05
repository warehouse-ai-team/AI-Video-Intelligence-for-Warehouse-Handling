'use client';

import { useState, useRef, useEffect } from 'react';
import { WarehouseEvent } from '@/lib/types';
import { askAssistant, AssistantMessage, SUGGESTED_QUESTIONS } from '@/lib/assistant';

interface ChatPanelProps {
  events: WarehouseEvent[];
  selectedEvent?: WarehouseEvent;
}

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

export default function ChatPanel({ events, selectedEvent }: ChatPanelProps) {
  const [messages, setMessages] = useState<AssistantMessage[]>([
    {
      id: makeId(),
      role: 'assistant',
      content:
        "I'm the warehouse supervisor assistant. Ask me about detected behaviours, risk levels, or a selected incident — I'll answer only from recorded event data.",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isThinking]);

  async function handleSend(question: string) {
    const trimmed = question.trim();
    if (!trimmed || isThinking) return;

    const userMessage: AssistantMessage = {
      id: makeId(),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsThinking(true);

    try {
      const answer = await askAssistant(trimmed, { events, selectedEvent });
      setMessages((prev) => [
        ...prev,
        { id: makeId(), role: 'assistant', content: answer, timestamp: new Date().toISOString() },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: 'assistant',
          content: "Something went wrong reaching the assistant. Please try again.",
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsThinking(false);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-panel border border-border bg-surface">
      <div className="border-b border-border px-4 py-2">
        <span className="text-sm font-medium text-text-primary">AI Supervisor Assistant</span>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-panel px-3 py-2 text-sm ${
                msg.role === 'user'
                  ? 'bg-accent text-base'
                  : 'border border-border bg-base text-text-primary'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {isThinking && (
          <div className="flex justify-start">
            <div className="rounded-panel border border-border bg-base px-3 py-2 text-sm text-text-muted">
              Thinking…
            </div>
          </div>
        )}
      </div>

      {messages.length <= 1 && (
        <div className="flex flex-wrap gap-2 border-t border-border px-3 py-2">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              className="rounded-badge border border-border px-2 py-1 text-xs text-text-muted transition-colors hover:border-accent hover:text-text-primary"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(input);
        }}
        className="flex gap-2 border-t border-border p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about an incident, bay, or behaviour…"
          className="flex-1 rounded-panel border border-border bg-base px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={isThinking || !input.trim()}
          className="rounded-panel bg-accent px-4 py-2 text-sm font-medium text-base disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}