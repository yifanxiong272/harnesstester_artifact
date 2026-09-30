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











  __testAugmentVitest_87485789cd03.it("add_paths_throws_on_limit_exceeded_round_001_pass_03", async () => {
    const vi = __testAugmentVitest_87485789cd03.vi;
    const expect = __testAugmentVitest_87485789cd03.expect;

    const fakeWatcher = {
      add: vi.fn(),
      unwatch: vi.fn(),
      on: vi.fn(),
      close: vi.fn(() => Promise.resolve()),
    } as unknown as import('chokidar').FSWatcher;

    const lookup = { resolve: (_id: string) => ({ send: (_f: unknown) => {} }) } as any;
    const logger = { warn: vi.fn(), debug: vi.fn() } as any;
    const sessionService = {} as any;

    const { FsWatcherService } = await __testAugmentLoadTarget_cd1877b8e188();

    // Set maxPathsPerConnection to 1 so adding two distinct paths for same connection triggers limit error
    const svc = new FsWatcherService(lookup, { watcherFactory: () => fakeWatcher as any, maxPathsPerConnection: 1 }, logger, sessionService);

    const p1 = '/lim/a.txt';
    const p2 = '/lim/b.txt';

    // First add should succeed
    expect(svc.addPaths('s-limit', 'c-limit', [p1])).toEqual([p1]);

    // Adding a second different path should throw due to exceeding maxPathsPerConnection
    __testAugmentVitest_87485789cd03.expect(() => svc.addPaths('s-limit', 'c-limit', [p2])).toThrow();
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
