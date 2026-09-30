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











  __testAugmentVitest_87485789cd03.it("forget_connection_cleans_up_sessions_round_001_pass_02", async () => {
    const vi = __testAugmentVitest_87485789cd03.vi;
    const expect = __testAugmentVitest_87485789cd03.expect;

    const listeners = new Map<string, (...args: any[]) => void>();
    const fakeWatcher = {
      add: vi.fn(),
      unwatch: vi.fn(),
      on: vi.fn((ev: string, cb: (...args: any[]) => void) => listeners.set(ev, cb)),
      close: vi.fn(() => Promise.resolve()),
    } as unknown as import('chokidar').FSWatcher;

    const lookup = { resolve: (_id: string) => ({ send: (_frame: unknown) => {/* noop */} }) } as any;
    const logger = { warn: vi.fn(), debug: vi.fn() } as any;
    const sessionService = {} as any;

    const { FsWatcherService } = await __testAugmentLoadTarget_cd1877b8e188();

    const svc = new FsWatcherService(lookup, { debounceMs: 10, watcherFactory: () => fakeWatcher as any }, logger, sessionService);

    // Add paths for two different sessions under same connection
    const p1 = '/forget/s1/a.txt';
    const p2 = '/forget/s2/b.txt';
    svc.addPaths('s1', 'conn-forget', [p1]);
    svc.addPaths('s2', 'conn-forget', [p2]);

    // Ensure watchers were added
    expect((fakeWatcher.add as any)).toHaveBeenCalledWith(p1);
    expect((fakeWatcher.add as any)).toHaveBeenCalledWith(p2);

    // Now forget the connection: this should cause removePaths to run for both sessions and unwatch both paths
    svc.forgetConnection('conn-forget');

    // After forget, watchedPaths should return empty for those sessions
    expect(svc.watchedPaths('conn-forget', 's1')).toEqual([]);
    expect(svc.watchedPaths('conn-forget', 's2')).toEqual([]);

    // The underlying watcher.unwatch should have been called for both paths during cleanup
    expect((fakeWatcher.unwatch as any).mock.calls.length).toBeGreaterThanOrEqual(2);
    const unwatched = (fakeWatcher.unwatch as any).mock.calls.flat().map(String);
    expect(unwatched).toEqual(expect.arrayContaining([p1, p2]));
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
