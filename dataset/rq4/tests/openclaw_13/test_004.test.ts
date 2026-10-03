import { it, expect } from 'vitest';
import { findCodeRegions } from '../../shared/text/code-regions';

it('does not report mismatched backtick-run inline code spans (opening 3 vs closing 2) on a single line', () => {
  const text = 'before ```a`` after';
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  expect(slices).not.toContain('```a``');
});
