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











  __testAugmentVitest_87485789cd03.it("add_paths_idempotent_returns_existing_round_001_pass_02", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    // fake watcher to observe add/unwatch calls
    const fakeWatcher = {
      add: __testAugmentVitest_87485789cd03.vi.fn(),
      unwatch: __testAugmentVitest_87485789cd03.vi.fn(),
      on: (_ev: string, _cb: Function) => {},
      close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined),
    } as any;

    const lookup = { resolve: (_id: string) => null };
    const logger = { debug: () => {}, warn: () => {} } as any;

    const svc = new FsWatcherService(lookup, { watcherFactory: () => fakeWatcher }, logger, {} as any);

    const sessionId = 's-idemp';
    const connectionId = 'c-idemp';
    const path = '/some/path/file.txt';

    const first = svc.addPaths(sessionId, connectionId, [path]);
    __testAugmentVitest_87485789cd03.expect(first).toEqual([path]);
    __testAugmentVitest_87485789cd03.expect(fakeWatcher.add).toHaveBeenCalledTimes(1);

    // adding the same path again should return the existing keys and not call watcher.add again
    const second = svc.addPaths(sessionId, connectionId, [path]);
    __testAugmentVitest_87485789cd03.expect(second).toEqual([path]);
    __testAugmentVitest_87485789cd03.expect(fakeWatcher.add).toHaveBeenCalledTimes(1);
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
