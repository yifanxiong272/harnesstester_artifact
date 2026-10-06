import { test, expect, vi } from 'vitest';

// Mock resolver-only / project-alias modules that are unavailable in the test harness.
// These mocks provide minimal exports required for module resolution and to avoid
// changing the target's runtime logic for the branch we exercise.
vi.mock('#/constants/canvas-ui', () => ({ CANVAS_UI_CLIENT_TOOL_NAME: 'mock-tool' }));
vi.mock('#/i18n', () => ({ default: { t: (k: any) => String(k) } }));
vi.mock('#/i18n/declaration', () => ({ I18nKey: {} }));
vi.mock('#/types/agent-server/core', () => ({}));
vi.mock('#/types/agent-server/core/base/observation', () => ({}));
vi.mock('./get-observation-result', () => ({ getObservationResult: (e: any) => e }));
vi.mock('./shared', () => ({ getDefaultEventContent: () => '', MAX_CONTENT_LENGTH: 10000 }));

// Use a dynamic import so that our vi.mock registrations take effect before
// the target module (and its aliased imports) are resolved by the loader.
test('files list formatting preserves exact count and presents one backtick-enclosed bullet per file even for filenames with backticks and newlines', async () => {
  const { getObservationContent } = await import('../../../src/components/conversation-events/chat/event-content-helpers/get-observation-content');

  const filenames = ["foo`bar", "baz\nqux"];

  const event: any = {
    observation: {
      kind: 'GlobObservation',
      is_error: false,
      truncated: false,
      files: filenames,
      pattern: 'pat',
      search_path: '/tmp',
      content: [{ type: 'text', text: 'some info' }],
    },
  };

  const rendered = getObservationContent(event);

  // Header: look for '**Files Found (<number>'
  const headerMatch = /\*\*Files Found \((\d+)/.exec(rendered);
  const headerCount = headerMatch ? Number(headerMatch[1]) : NaN;

  const lines = rendered.split('\n');
  const bulletLines = lines.filter((l) => l.startsWith('- `') && l.endsWith('`'));
  const extracted = bulletLines.map((l) => l.slice(3, -1));

  const headerMatchesCount = headerCount === bulletLines.length && headerCount === filenames.length;

  // Each extracted bullet must exactly match one of the original filenames (including embedded newlines/backticks)
  const allMatchOriginal = extracted.every((e) => filenames.includes(e));

  const ok = headerMatchesCount && extracted.length === filenames.length && allMatchOriginal;

  expect(ok).toBe(true);
});
