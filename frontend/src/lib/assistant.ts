import { WarehouseEvent } from './types';

export interface AssistantMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

// Sample supervisor-style questions from the execution plan, used to seed
// suggested prompts in the UI.
export const SUGGESTED_QUESTIONS = [
  'Which behaviour happened most frequently?',
  'Which bay has the highest risk?',
  'Why was this incident classified as high risk?',
  'Show me recent critical incidents.',
];

// TEMPORARY mock — Milestone 6/7 replaces this with a real call to
// ai_assistant/ via the backend. Keeps the same signature so ChatPanel
// doesn't need to change when that happens.
export async function askAssistant(
  question: string,
  context: { events: WarehouseEvent[]; selectedEvent?: WarehouseEvent }
): Promise<string> {
  await new Promise((resolve) => setTimeout(resolve, 500)); // simulate latency

  const lower = question.toLowerCase();

  if (lower.includes('why') && context.selectedEvent) {
    const e = context.selectedEvent;
    return `${e.behaviour_type.replace(/_/g, ' ')} was classified as ${e.risk_level} risk. ${
      e.risk_explanation ?? 'No further explanation is recorded for this event.'
    } (This is a mock response — Milestone 6 connects this to the real risk engine data.)`;
  }

  if (lower.includes('most frequent') || lower.includes('most common')) {
    const counts: Record<string, number> = {};
    context.events.forEach((e) => {
      counts[e.behaviour_type] = (counts[e.behaviour_type] ?? 0) + 1;
    });
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
    return top
      ? `The most frequent behaviour is "${top[0].replace(/_/g, ' ')}" with ${top[1]} occurrence(s) in the currently loaded events. (Mock response.)`
      : 'No events are currently loaded.';
  }

  if (lower.includes('bay')) {
    const counts: Record<string, number> = {};
    context.events.forEach((e) => {
      if (e.bay) counts[e.bay] = (counts[e.bay] ?? 0) + 1;
    });
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1])[0];
    return top
      ? `${top[0]} has the most recorded incidents (${top[1]}). (Mock response — will query the backend's bay-comparison endpoint once connected.)`
      : 'No bay data is currently loaded.';
  }

  if (lower.includes('critical')) {
    const criticalEvents = context.events.filter((e) => e.risk_level === 'critical');
    return criticalEvents.length > 0
      ? `There are ${criticalEvents.length} critical event(s), most recently "${criticalEvents[0].behaviour_type.replace(/_/g, ' ')}" in ${criticalEvents[0].bay ?? 'an unspecified bay'}.`
      : 'No critical events are currently recorded.';
  }

  return "I can only answer using recorded event data — I don't have information on that yet. Try asking about behaviour frequency, risk levels, or a specific selected event.";
}