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











  __testAugmentVitest_87485789cd03.it("add_paths_enforce_limit_round_001", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    // simple lookup and logger stubs
    const lookup = { resolve: (_id: string) => null };
    const logger = { debug: () => {}, warn: () => {} } as any;

    // create service with a very small maxPathsPerConnection to trigger the limit
    const svc = new FsWatcherService(lookup, { maxPathsPerConnection: 1 }, logger, {} as any);

    // Adding two distinct paths for the same session/connection should throw synchronously
    const sessionId = 's1';
    const connectionId = 'c1';
    __testAugmentVitest_87485789cd03.expect(() => {
      svc.addPaths(sessionId, connectionId, ['/root/a', '/root/b']);
    }).toThrow();
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
