import { WarehouseEvent } from './types';

const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export interface AssistantMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

export const SUGGESTED_QUESTIONS = [
  'Which behaviour happened most frequently?',
  'Which bay has the highest risk?',
  'Why was this incident classified as high risk?',
  'Show me recent critical incidents.',
];

interface ChatApiResponse {
  answer: string;
  tools_used: string[];
}

// Real call to backend/app/api/assistant.py's POST /assistant/chat.
// Same signature as the Milestone 4 mock — nothing calling this needs to change.
export async function askAssistant(
  question: string,
  context: { events: WarehouseEvent[]; selectedEvent?: WarehouseEvent }
): Promise<string> {
  try {
    const res = await fetch(`${BASE_URL}/assistant/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        selected_event_id: context.selectedEvent?.event_id ?? null,
      }),
    });

    if (!res.ok) {
      throw new Error(`Assistant request failed (${res.status})`);
    }

    const data: ChatApiResponse = await res.json();
    return data.answer;
  } catch {
    return "I couldn't reach the assistant service right now. Please try again in a moment.";
  }
}