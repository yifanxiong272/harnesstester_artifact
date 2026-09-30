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











  __testAugmentVitest_87485789cd03.it("flush_non_truncated_sends_relpath_and_kind_round_001", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    // capture the 'all' event handler from the fake watcher so we can simulate chokidar events
    let handlers: Record<string, Function> = {};
    const fakeWatcher = {
      add: __testAugmentVitest_87485789cd03.vi.fn(),
      unwatch: __testAugmentVitest_87485789cd03.vi.fn(),
      on: (ev: string, cb: Function) => { handlers[ev] = cb; },
      close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined),
    } as any;

    // create a sink that will receive frames via send
    const sentFrames: any[] = [];
    const sink = { send: (frame: any) => sentFrames.push(frame) };
    const lookup = { resolve: (_id: string) => sink };
    const logger = { debug: () => {}, warn: () => {} } as any;

    // Use a non-zero debounce but use fake timers so flushWindow is triggered deterministically
    const svc = new FsWatcherService(lookup, { watcherFactory: () => fakeWatcher, debounceMs: 100 }, logger, {} as any);

    const sessionId = 'sflush';
    const connectionId = 'cflush';

    // add path so the connection/session mapping exists
    svc.addPaths(sessionId, connectionId, ['/root/project/file.txt']);

    // use fake timers to control setTimeout -> set up and advance later
    __testAugmentVitest_87485789cd03.vi.useFakeTimers();

    // simulate a chokidar 'add' event (maps to action 'created' and kind 'file')
    handlers['all']?.('add', '/root/project/file.txt');

    // advance timers to trigger flushWindow
    __testAugmentVitest_87485789cd03.vi.advanceTimersByTime(500);
    // let any pending microtasks run
    await Promise.resolve();

    // restore timers
    __testAugmentVitest_87485789cd03.vi.useRealTimers();

    __testAugmentVitest_87485789cd03.expect(sentFrames).toHaveLength(1);
    const frame = sentFrames[0];
    __testAugmentVitest_87485789cd03.expect(frame.type).toBe('event.fs.changed');
    __testAugmentVitest_87485789cd03.expect(frame.session_id).toBe(sessionId);
    __testAugmentVitest_87485789cd03.expect(frame.payload.coalesced_window_ms).toBe(100);
    __testAugmentVitest_87485789cd03.expect(frame.payload.changes).toHaveLength(1);
    __testAugmentVitest_87485789cd03.expect(frame.payload.changes[0].path).toBe('file.txt');
    __testAugmentVitest_87485789cd03.expect(frame.payload.changes[0].change).toBe('created');
    __testAugmentVitest_87485789cd03.expect(frame.payload.changes[0].kind).toBe('file');
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
