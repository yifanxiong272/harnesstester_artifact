import { it, expect } from 'vitest';
import { findCodeRegions } from '../../shared/text/code-regions';

it('does not report a single inline region for mismatched backtick run lengths on one line', () => {
  const text = 'before ```a`` after';
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  expect(slices).not.toContain('```a``');
});
