import { test, expect } from 'vitest';
import { buildFtsQuery } from '../../memory/hybrid';

// Single top-level test that exercises the public entrypoint and makes one assertion.
test('buildFtsQuery preserves Unicode letters as a single token', () => {
  expect(buildFtsQuery('mañana')).toBe(`"mañana"`);
});
