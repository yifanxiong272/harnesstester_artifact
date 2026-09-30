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











  __testAugmentVitest_87485789cd03.it("sends_relative_file_change_round_001", async () => {
    const vi = __testAugmentVitest_87485789cd03.vi;
    const expect = __testAugmentVitest_87485789cd03.expect;

    // Use fake timers so debounce is deterministic
    vi.useFakeTimers();

    // Create a fake watcher that records the registered listeners and supports add/unwatch/close
    const listeners = new Map<string, (...args: any[]) => void>();
    const fakeWatcher = {
      add: vi.fn(),
      unwatch: vi.fn(),
      on: vi.fn((ev: string, cb: (...args: any[]) => void) => {
        listeners.set(ev, cb);
      }),
      close: vi.fn(() => Promise.resolve()),
    } as unknown as import('chokidar').FSWatcher;

    // Fake lookup that returns a sink capturing sent frames
    const sent: any[] = [];
    const lookup = {
      resolve: (_id: string) => ({ send: (frame: unknown) => sent.push(frame) }),
    } as any;

    // logger and session service dummies
    const logger = { warn: vi.fn(), debug: vi.fn() } as any;
    const sessionService = {} as any;

    const { FsWatcherService } = await __testAugmentLoadTarget_cd1877b8e188();

    // Create service with tiny debounce and our fake watcher
    const svc = new FsWatcherService(lookup, { debounceMs: 10, watcherFactory: () => fakeWatcher as any }, logger, sessionService);

    // Add a single absolute path - should cause watcher.add to be called
    const absPath = '/root/project/file.txt';
    const res = svc.addPaths('sess1', 'conn1', [absPath]);
    // The return should include the tracked path
    expect(res).toEqual([absPath]);
    expect((fakeWatcher.add as any)).toHaveBeenCalledWith(absPath);

    // Trigger the 'all' handler as chokidar would (eventName, absPath)
    const allCb = listeners.get('all')!;
    allCb('add', absPath);

    // Advance timers so flushWindow runs
    vi.advanceTimersByTime(50);
    vi.useRealTimers();

    // Verify a frame was sent and the relative posix path is used
    expect(sent).toHaveLength(1);
    const frame = sent[0] as any;
    expect(frame.type).toBe('event.fs.changed');
    expect(frame.payload.coalesced_window_ms).toBe(10);
    expect(frame.payload.changes).toHaveLength(1);
    expect(frame.payload.changes[0]).toMatchObject({ path: 'file.txt', change: 'created', kind: 'file' });
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
