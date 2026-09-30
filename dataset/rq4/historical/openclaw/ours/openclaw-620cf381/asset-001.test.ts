import { it, expect } from 'vitest';
import { normalizeTargetForProvider } from '../../infra/outbound/target-normalization';

it('normalizeTargetForProvider should trim only and preserve case when provider is empty', () => {
  const provider = '';
  const raw = ' AbC123 ';
  const result = normalizeTargetForProvider(provider, raw);
  expect(result).toBe('AbC123');
});
