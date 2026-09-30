import { test, expect } from 'vitest';
import { mergeStreamingText } from '../../../extensions/feishu/src/streaming-card';

test('mergeStreamingText resolves suffix/prefix overlap without duplicating characters', () => {
  const previous = 'hel';
  const next = 'ello';

  const merged = mergeStreamingText(previous, next);

  expect(merged).toBe('hello');
});
