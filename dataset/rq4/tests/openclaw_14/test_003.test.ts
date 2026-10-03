import { test, expect } from 'vitest';
import { sanitizeForPlainText } from '../../infra/outbound/sanitize-text';

test('sanitizeForPlainText converts block-level tags with attributes to surrounding newlines', () => {
  const p = sanitizeForPlainText('<p class="x">para</p>');
  const d = sanitizeForPlainText('<div id="y">block</div>');
  // Single assertion combining both expectations
  expect(p === '\npara\n' && d === '\nblock\n').toBe(true);
});
