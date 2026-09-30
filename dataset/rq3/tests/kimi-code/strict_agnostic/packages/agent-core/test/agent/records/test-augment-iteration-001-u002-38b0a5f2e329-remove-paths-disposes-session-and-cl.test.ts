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











  __testAugmentVitest_87485789cd03.it("remove_paths_disposes_session_and_closes_watcher_round_001", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    // Create a fake FSWatcher that records calls to close, add, unwatch
    let registeredHandlers: Record<string, Function> = {};
    const fakeWatcher = {
      add: __testAugmentVitest_87485789cd03.vi.fn(),
      unwatch: __testAugmentVitest_87485789cd03.vi.fn(),
      on: (ev: string, cb: Function) => { registeredHandlers[ev] = cb; },
      close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined),
    } as any;

    const lookup = { resolve: (_id: string) => null };
    const logger = { debug: () => {}, warn: () => {} } as any;

    // Provide watcherFactory so session creation uses our fakeWatcher
    const svc = new FsWatcherService(lookup, { watcherFactory: () => fakeWatcher }, logger, {} as any);

    const sessionId = 'sess-1';
    const connectionId = 'conn-1';
    // add a single path -> should create session and cause watcher to be used
    const watched = svc.addPaths(sessionId, connectionId, ['/root/one/file.txt']);
    __testAugmentVitest_87485789cd03.expect(watched).toContain('/root/one/file.txt');

    // remove the path; this should dispose the reference and ultimately call close on watcher
    const left = svc.removePaths(sessionId, connectionId, ['/root/one/file.txt']);
    __testAugmentVitest_87485789cd03.expect(left).toHaveLength(0);

    // Because the session should have been removed and disposed, watcher.close should have been invoked
    __testAugmentVitest_87485789cd03.expect(fakeWatcher.close).toHaveBeenCalled();
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
