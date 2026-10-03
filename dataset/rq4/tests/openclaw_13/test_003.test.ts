import { test, expect } from 'vitest';
import { findCodeRegions } from '../../shared/text/code-regions';

test('findCodeRegions should not treat mismatched backtick counts as inline code span', () => {
  const text = 'before ```a`` after';
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  expect(slices).not.toContain('```a``');
});
