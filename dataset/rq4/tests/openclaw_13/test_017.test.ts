import { test, expect } from 'vitest';
import { findCodeRegions } from '../../shared/text/code-regions';

test('findCodeRegions should not report a mismatched backtick-run sequence (```a``) as inline code on a single line', () => {
  const text = 'before ```a`` after';
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  expect(slices).not.toContain('```a``');
});
