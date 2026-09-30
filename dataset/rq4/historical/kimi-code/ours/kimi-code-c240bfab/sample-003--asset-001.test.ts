import { it, expect } from 'vitest';
import { reduceWireRecords } from '../../../src/services/message/transcript';

it('reduceWireRecords should not emit a standalone tool entry for an orphan tool.result', () => {
  const orphanId = 'orphan';

  // Deterministic single-record iterable: a loop-record event with no prior tool.call
  const records = [
    {
      type: 'context.append_loop_event',
      event: {
        type: 'tool.result',
        toolCallId: orphanId,
        // Deterministic result payload used to form any potential TranscriptEntry content
        result: { isError: false, value: 'deterministic' },
      },
    },
  ];

  // Exercise the public entrypoint under test
  const transcript = reduceWireRecords(records);

  // Primary oracle: there must be no entry with role 'tool' and toolCallId 'orphan'
  const hasOrphanToolEntry = transcript.entries.some((e: any) =>
    e?.message?.role === 'tool' && e?.message?.toolCallId === orphanId
  );

  expect(hasOrphanToolEntry).toBe(false);
});
