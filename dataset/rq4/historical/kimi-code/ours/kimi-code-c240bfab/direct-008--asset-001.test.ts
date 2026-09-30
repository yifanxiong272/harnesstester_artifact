import { test, expect } from 'vitest';
import { reduceWireRecords } from '../../../src/services/message/transcript';

// Single top-level test exercising the public entrypoint reduceWireRecords.
// Construct a deterministic iterable with a lone tool.result loop event
// for toolCallId 'orphan' and assert that no emitted transcript entry
// has role 'tool' with that toolCallId.
test('reduceWireRecords does not emit an orphan tool entry for a lone tool.result', () => {
  const records: any[] = [
    {
      type: 'context.append_loop_event',
      event: {
        type: 'tool.result',
        toolCallId: 'orphan',
        result: { isError: false, value: 'x' },
      },
      time: 123,
    },
  ];

  const transcript = reduceWireRecords(records);
  const hasOrphanToolEntry = transcript.entries.some((e: any) =>
    e?.message?.role === 'tool' && e?.message?.toolCallId === 'orphan'
  );

  expect(hasOrphanToolEntry).toBe(false);
});
