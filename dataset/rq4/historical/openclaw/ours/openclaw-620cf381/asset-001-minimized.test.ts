import { test, expect } from 'vitest';
import { normalizeTargetForProvider } from '../../infra/outbound/target-normalization';

test('normalizeTargetForProvider trims but preserves case when no plugin', () => {
  const raw = '  AbC123  ';
  const result = normalizeTargetForProvider('', raw);
  expect(result).toBe('AbC123');
});
