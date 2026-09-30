import { describe, expect, it } from 'vitest';

import { buildReplay } from '../../../src';
import {
  AGENT_WIRE_PROTOCOL_VERSION,
  InMemoryAgentRecordPersistence,
  type AgentRecord,
} from '../../../src/agent/records';
import type { ContextMessage } from '../../../src/agent/context';
import { testAgent } from '../harness/agent';

describe('AgentRecords persistence metadata', () => {











  __testAugmentVitest_87485789cd03.it("truncated_window_sends_truncated_flag_and_count_round_001", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    let handlers: Record<string, Function> = {};
    const fakeWatcher = {
      add: __testAugmentVitest_87485789cd03.vi.fn(),
      unwatch: __testAugmentVitest_87485789cd03.vi.fn(),
      on: (ev: string, cb: Function) => { handlers[ev] = cb; },
      close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined),
    } as any;

    const sentFrames: any[] = [];
    const sink = { send: (frame: any) => sentFrames.push(frame) };
    const lookup = { resolve: (_id: string) => sink };
    const logger = { debug: () => {}, warn: () => {} } as any;

    // Set maxChangesPerWindow to 1 so adding two events will mark the entry as truncated
    const svc = new FsWatcherService(lookup, { watcherFactory: () => fakeWatcher, debounceMs: 50, maxChangesPerWindow: 1 }, logger, {} as any);

    const sessionId = 'strip';
    const connectionId = 'conn-strip';
    svc.addPaths(sessionId, connectionId, ['/root/p/file.txt']);

    __testAugmentVitest_87485789cd03.vi.useFakeTimers();

    // emit two events within the same debounce window
    handlers['all']?.('change', '/root/p/file.txt');
    handlers['all']?.('change', '/root/p/file.txt');

    // advance timers to flush
    __testAugmentVitest_87485789cd03.vi.advanceTimersByTime(200);
    await Promise.resolve();
    __testAugmentVitest_87485789cd03.vi.useRealTimers();

    __testAugmentVitest_87485789cd03.expect(sentFrames).toHaveLength(1);
    const frame = sentFrames[0];
    __testAugmentVitest_87485789cd03.expect(frame.payload.truncated).toBe(true);
    __testAugmentVitest_87485789cd03.expect(frame.payload.count).toBeGreaterThanOrEqual(2);
  });
});


class RecordingInMemoryAgentRecordPersistence extends InMemoryAgentRecordPersistence {
  readonly rewrites: AgentRecord[][] = [];

  override rewrite(records: readonly AgentRecord[]): void {
    this.rewrites.push([...records]);
    super.rewrite(records);
  }
}

function userMessage(text: string): ContextMessage {
  return {
    role: 'user',
    content: [{ type: 'text', text }],
    toolCalls: [],
  };
}

import * as __testAugmentVitest_87485789cd03 from "vitest";

const __testAugmentLoadTarget_cd1877b8e188 = async () => {
  __testAugmentVitest_87485789cd03.vi.doUnmock("../../../src/services/fs/fsWatcherService.js");
  __testAugmentVitest_87485789cd03.vi.resetModules();
  return import("../../../src/services/fs/fsWatcherService.js");
};
