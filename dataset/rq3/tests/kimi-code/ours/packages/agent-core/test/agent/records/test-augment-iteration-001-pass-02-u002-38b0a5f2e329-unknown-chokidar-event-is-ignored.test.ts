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











  __testAugmentVitest_87485789cd03.it("unknown_chokidar_event_is_ignored_round_001_pass_02", async () => {
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

    const sent: any[] = [];
    const lookup = { resolve: (_id: string) => ({ send: (frame: unknown) => sent.push(frame) }) } as any;
    const logger = { warn: vi.fn(), debug: vi.fn() } as any;
    const sessionService = {} as any;

    const { FsWatcherService } = await __testAugmentLoadTarget_cd1877b8e188();

    const svc = new FsWatcherService(lookup, { debounceMs: 10, watcherFactory: () => fakeWatcher as any }, logger, sessionService);

    const p = '/ignore/this.txt';
    svc.addPaths('sess-ignore', 'conn-ignore', [p]);

    // Emit an event that mapChokidarEventToAction maps to undefined
    const allCb = listeners.get('all')!;
    allCb('someUnknownEvent', p);

    // Advance timers to ensure if any debounce were scheduled it would fire
    vi.advanceTimersByTime(50);
    vi.useRealTimers();

    // No frames should have been sent because the event is ignored
    expect(sent).toHaveLength(0);
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
