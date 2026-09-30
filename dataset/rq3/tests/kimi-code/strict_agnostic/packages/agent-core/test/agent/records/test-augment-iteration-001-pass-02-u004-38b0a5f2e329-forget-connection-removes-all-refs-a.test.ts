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











  __testAugmentVitest_87485789cd03.it("forget_connection_removes_all_refs_and_closes_watchers_round_001_pass_02", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    // prepare two fake watchers (one per session) so close calls are observable
    const watcherA = { add: __testAugmentVitest_87485789cd03.vi.fn(), unwatch: __testAugmentVitest_87485789cd03.vi.fn(), on: (_: any, __: any) => {}, close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined) } as any;
    const watcherB = { add: __testAugmentVitest_87485789cd03.vi.fn(), unwatch: __testAugmentVitest_87485789cd03.vi.fn(), on: (_: any, __: any) => {}, close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined) } as any;

    // watcherFactory will return different watcher instances for successive session creations
    let called = 0;
    const factory = () => (++called === 1 ? watcherA : watcherB);

    const lookup = { resolve: (_id: string) => null };
    const logger = { debug: () => {}, warn: () => {} } as any;

    const svc = new FsWatcherService(lookup, { watcherFactory: factory }, logger, {} as any);

    // Create two sessions under the same connection
    svc.addPaths('sess-a', 'conn-x', ['/a/one.txt']);
    svc.addPaths('sess-b', 'conn-x', ['/b/two.txt']);

    // Ensure watchedPaths reports the entries for each session before forget
    __testAugmentVitest_87485789cd03.expect(svc.watchedPaths('conn-x', 'sess-a')).toEqual(['/a/one.txt']);
    __testAugmentVitest_87485789cd03.expect(svc.watchedPaths('conn-x', 'sess-b')).toEqual(['/b/two.txt']);

    // forget the connection - should dispose both sessions and close both watchers
    svc.forgetConnection('conn-x');

    // after forgetting, watchedPaths should return empty arrays
    __testAugmentVitest_87485789cd03.expect(svc.watchedPaths('conn-x', 'sess-a')).toEqual([]);
    __testAugmentVitest_87485789cd03.expect(svc.watchedPaths('conn-x', 'sess-b')).toEqual([]);

    __testAugmentVitest_87485789cd03.expect(watcherA.close).toHaveBeenCalled();
    __testAugmentVitest_87485789cd03.expect(watcherB.close).toHaveBeenCalled();
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
