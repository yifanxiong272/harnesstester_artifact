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











  __testAugmentVitest_87485789cd03.it("session_dispose_clears_debounce_timer_round_001_pass_02", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    // fake watcher and handler capture
    let handlers: Record<string, Function> = {};
    const fakeWatcher = {
      add: __testAugmentVitest_87485789cd03.vi.fn(),
      unwatch: __testAugmentVitest_87485789cd03.vi.fn(),
      on: (ev: string, cb: Function) => { handlers[ev] = cb; },
      close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined),
    } as any;

    const lookup = { resolve: (_id: string) => null };
    const logger = { debug: () => {}, warn: () => {} } as any;

    const svc = new FsWatcherService(lookup, { watcherFactory: () => fakeWatcher, debounceMs: 1000 }, logger, {} as any);

    const sessionId = 's-dispose';
    const connectionId = 'c-dispose';
    svc.addPaths(sessionId, connectionId, ['/tmp/x.txt']);

    // spy on clearTimeout to ensure dispose clears any timer
    const spyClear = __testAugmentVitest_87485789cd03.vi.spyOn(globalThis as any, 'clearTimeout');

    // trigger a raw change which will set a debounce timer
    handlers['all']?.('change', '/tmp/x.txt');

    // Now remove the path which should dispose the session and call clearTimeout
    svc.removePaths(sessionId, connectionId, ['/tmp/x.txt']);

    __testAugmentVitest_87485789cd03.expect(spyClear).toHaveBeenCalled();

    spyClear.mockRestore();
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
