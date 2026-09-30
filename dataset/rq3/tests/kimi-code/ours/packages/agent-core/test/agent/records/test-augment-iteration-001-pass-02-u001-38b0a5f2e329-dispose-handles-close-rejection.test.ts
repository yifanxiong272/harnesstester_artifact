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











  __testAugmentVitest_87485789cd03.it("dispose_handles_close_rejection_round_001_pass_02", async () => {
    const vi = __testAugmentVitest_87485789cd03.vi;
    const expect = __testAugmentVitest_87485789cd03.expect;

    // Fake watcher whose close rejects so SessionEntry.dispose logs a warn
    const listeners = new Map<string, (...args: any[]) => void>();
    const fakeWatcher = {
      add: vi.fn(),
      unwatch: vi.fn(),
      on: vi.fn((ev: string, cb: (...args: any[]) => void) => listeners.set(ev, cb)),
      close: vi.fn(() => Promise.reject(new Error('close failed'))),
    } as unknown as import('chokidar').FSWatcher;

    const sent: any[] = [];
    const lookup = { resolve: (_id: string) => ({ send: (frame: unknown) => sent.push(frame) }) } as any;
    const logger = { warn: vi.fn(), debug: vi.fn() } as any;
    const sessionService = {} as any;

    const { FsWatcherService } = await __testAugmentLoadTarget_cd1877b8e188();

    const svc = new FsWatcherService(lookup, { debounceMs: 10, watcherFactory: () => fakeWatcher as any }, logger, sessionService);

    // Add a single path (creates SessionEntry and will later dispose it when removed)
    const p = '/tmp/dispose/me.txt';
    svc.addPaths('sess-dispose', 'conn-dispose', [p]);

    // Remove the only path for that session/connection => should trigger disposal of the SessionEntry
    const remaining = svc.removePaths('sess-dispose', 'conn-dispose', [p]);
    expect(remaining).toEqual([]);

    // The SessionEntry.dispose calls watcher.close(). Its rejection is caught and logged.
    // Wait one tick for the rejection handler to run
    await new Promise((r) => setTimeout(r, 0));

    expect((fakeWatcher.close as any)).toHaveBeenCalled();
    expect(logger.warn).toHaveBeenCalled();
    // second argument is the logged message per implementation
    const lastCall = (logger.warn as any).mock.calls[(logger.warn as any).mock.calls.length - 1];
    expect(lastCall[1]).toBe('fs-watcher close failed');
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
