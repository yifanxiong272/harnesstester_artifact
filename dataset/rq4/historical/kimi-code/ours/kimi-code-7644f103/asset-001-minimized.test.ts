import { it, expect } from 'vitest';
import { project } from '../../../src/agent/context/projector';

it('removes assistant placeholder messages whose text parts are empty strings', () => {
  const history = [
    { role: 'user', content: [{ type: 'text', text: 'User start' }], toolCalls: [] },
    { role: 'assistant', content: [{ type: 'text', text: '' }], toolCalls: [] },
    { role: 'assistant', content: [{ type: 'text', text: 'real reply' }], toolCalls: [] },
    { role: 'user', content: [{ type: 'text', text: 'User followup' }], toolCalls: [] },
  ] as any;

  const projected = project(history as any);

  const simplified = projected.map((m: any) => ({
    role: m.role,
    text: (m.content || [])
      .map((p: any) => (p && p.type === 'text' ? p.text : ''))
      .join(''),
    toolCallsCount: (m.toolCalls || []).length,
  }));

  expect(simplified).toEqual([
    { role: 'user', text: 'User start', toolCallsCount: 0 },
    { role: 'assistant', text: 'real reply', toolCallsCount: 0 },
    { role: 'user', text: 'User followup', toolCallsCount: 0 },
  ]);
});
