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











  __testAugmentVitest_87485789cd03.it("send_error_is_logged_not_thrown_round_001", async () => {
    const vi = __testAugmentVitest_87485789cd03.vi;
    const expect = __testAugmentVitest_87485789cd03.expect;

    vi.useFakeTimers();
    const listeners = new Map<string, (...args: any[]) => void>();
    const fakeWatcher = {
      add: vi.fn(),
      unwatch: vi.fn(),
      on: vi.fn((ev: string, cb: (...args: any[]) => void) => listeners.set(ev, cb)),
      close: vi.fn(() => Promise.resolve()),
    } as unknown as import('chokidar').FSWatcher;

    // Sink that throws when send is called
    const lookup = { resolve: (_id: string) => ({ send: (_frame: unknown) => { throw new Error('boom'); } }) } as any;

    const logger = { warn: vi.fn(), debug: vi.fn() } as any;
    const sessionService = {} as any;

    const { FsWatcherService } = await __testAugmentLoadTarget_cd1877b8e188();
    const svc = new FsWatcherService(lookup, { debounceMs: 10, watcherFactory: () => fakeWatcher as any }, logger, sessionService);

    const p = '/x/y/z.txt';
    svc.addPaths('sess-ex', 'conn-ex', [p]);

    const allCb = listeners.get('all')!;
    allCb('change', p);

    // Allow debounce to fire and flushWindow to attempt send
    vi.advanceTimersByTime(50);
    vi.useRealTimers();

    // Even though send threw, service should catch and call logger.warn
    expect(logger.warn).toHaveBeenCalled();
    // The message should be the expected literal
    const lastCall = (logger.warn as any).mock.calls[(logger.warn as any).mock.calls.length - 1];
    expect(lastCall[1]).toBe('fs-watcher send failed');
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
