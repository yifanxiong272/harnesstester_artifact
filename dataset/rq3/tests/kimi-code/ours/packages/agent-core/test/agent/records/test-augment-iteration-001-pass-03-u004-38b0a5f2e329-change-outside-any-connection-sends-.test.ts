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











  __testAugmentVitest_87485789cd03.it("change_outside_any_connection_sends_no_frame_round_001_pass_03", async () => {
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

    // Create a service and add a watched path for connA
    const svc = new FsWatcherService(lookup, { debounceMs: 10, watcherFactory: () => fakeWatcher as any }, logger, sessionService);
    svc.addPaths('sess-x', 'conn-x', ['/watched/base']);

    // Emit a change for a path that is not under any watched parent
    const allCb = listeners.get('all')!;
    allCb('change', '/unrelated/path/file.txt');

    // Advance timers - flushWindow runs but should skip sending because no perConnChanges matched
    vi.advanceTimersByTime(50);
    vi.useRealTimers();

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
