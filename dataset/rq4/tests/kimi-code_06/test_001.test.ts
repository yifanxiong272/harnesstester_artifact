import { it, expect } from 'vitest';
import { renderToolResultForModel } from '../../../src/agent/context/tool-result-render';

const textPart = (t: string) => ({ type: 'text', text: t } as const);

it('collapses a single whitespace-only text part to the combined empty-error status', () => {
  const out = renderToolResultForModel({
    output: [textPart('  \n  ')],
    isError: true,
  });

  expect(out).toEqual([
    textPart('<system>ERROR: Tool execution failed. Tool output is empty.</system>'),
  ]);
});
