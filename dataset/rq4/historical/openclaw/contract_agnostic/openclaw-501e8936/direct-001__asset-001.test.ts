import { test, expect } from 'vitest';
import { buildFtsQuery } from '../../memory/hybrid';

test('buildFtsQuery preserves Unicode words as single tokens for accented letters', () => {
  const input = 'café naïve 123_about';
  const out = buildFtsQuery(input);
  expect(out).toBe('"café" AND "naïve" AND "123_about"');
});
