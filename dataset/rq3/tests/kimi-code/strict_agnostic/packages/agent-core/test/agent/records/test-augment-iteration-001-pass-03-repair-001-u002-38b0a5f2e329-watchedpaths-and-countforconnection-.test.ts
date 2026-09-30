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











  __testAugmentVitest_87485789cd03.it("watchedPaths_and_countForConnection_defaults_round_001_pass_03", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    // fake watcher (simple) and logger/lookup stubs
    const fakeWatcher = { add: __testAugmentVitest_87485789cd03.vi.fn(), unwatch: __testAugmentVitest_87485789cd03.vi.fn(), on: () => {}, close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined) } as any;
    const lookup = { resolve: (_: string) => null };
    const logger = { debug: () => {}, warn: () => {} } as any;

    const svc = new FsWatcherService(lookup, { watcherFactory: () => fakeWatcher }, logger, {} as any);

    // asking for watchedPaths on unknown connection/session should return an empty array
    __testAugmentVitest_87485789cd03.expect(svc.watchedPaths('no-conn', 'no-session')).toEqual([]);

    // countForConnection on unknown connection should be zero
    __testAugmentVitest_87485789cd03.expect(svc.countForConnection('no-conn')).toBe(0);

    // addPaths then verify countForConnection reflects the addition
    svc.addPaths('s1', 'c1', ['/x/y.txt']);
    __testAugmentVitest_87485789cd03.expect(svc.countForConnection('c1')).toBe(1);

    // watchedPaths for that session should return the added path
    __testAugmentVitest_87485789cd03.expect(svc.watchedPaths('c1', 's1')).toEqual(['/x/y.txt']);
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
