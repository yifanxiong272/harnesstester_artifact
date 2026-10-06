import { it, expect } from 'vitest';
import { findCodeRegions } from '../../shared/text/code-regions';

const text = 'before ```a`` after';

it('does not treat mismatched backtick runs on a single line as an inline code region', () => {
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  expect(slices).not.toContain('```a``');
});
