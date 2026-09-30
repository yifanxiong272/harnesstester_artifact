import { it, expect } from 'vitest';
import { project } from '../../../src/agent/context/projector';

it('omits an empty assistant placeholder and merges adjacent explicit-user messages with exactly one blank line', () => {
  const history = [
    {
      role: 'user',
      content: [{ type: 'text', text: 'First user prompt' }],
      toolCalls: [],
      origin: { kind: 'user' },
    },
    {
      role: 'assistant',
      content: [{ type: 'text', text: '' }],
      toolCalls: [],
      // partial is intentionally absent (undefined) to match activation condition
    },
    {
      role: 'user',
      content: [{ type: 'text', text: 'Second user prompt' }],
      toolCalls: [],
      origin: { kind: 'user' },
    },
  ];

  const projected = project(history);

  expect(projected).toEqual([
    {
      role: 'user',
      content: [{ type: 'text', text: 'First user prompt\n\nSecond user prompt' }],
      toolCalls: [],
    },
  ]);
});
