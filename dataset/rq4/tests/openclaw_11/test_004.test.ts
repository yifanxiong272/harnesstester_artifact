import { it, expect } from 'vitest';
import { extractAssistantText } from "../../agents/pi-embedded-utils";

it('removes self-closing <thinking/> tags without dropping following text', () => {
  const msg = {
    role: 'assistant',
    content: [{ type: 'text', text: 'Before<thinking/>After' }],
    timestamp: 0,
  } as any;

  const result = extractAssistantText(msg);
  expect(result).toBe('BeforeAfter');
});
