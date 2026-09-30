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











  __testAugmentVitest_87485789cd03.it("default_watcher_factory_and_ignored_regex_round_001_pass_03", async () => {
    // Mock chokidar so the service's default watcherFactory constructs our FSWatcher
    __testAugmentVitest_87485789cd03.vi.doMock('chokidar', () => {
      class FSWatcher {
        public static lastOpts: any;
        constructor(opts: any) {
          // expose the constructed options via a global slot that the test can read
          (globalThis as any).__TEST_LAST_FS_OPTS = opts;
          (FSWatcher as any).lastOpts = opts;
        }
        on() {}
        add() {}
        unwatch() {}
        close() { return Promise.resolve(); }
      }
      return { FSWatcher };
    });

    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    const lookup = { resolve: (_: string) => null };
    const logger = { debug: () => {}, warn: () => {} } as any;

    // Construct without providing watcherFactory to exercise the default
    const svc = new FsWatcherService(lookup, {}, logger, {} as any);

    // Create a session so the default factory is invoked and the FSWatcher constructed
    svc.addPaths('sess-default', 'conn-default', ['/some/repo/.git/config']);

    // Inspect the global slot set by the mocked FSWatcher constructor
    const opts = (globalThis as any).__TEST_LAST_FS_OPTS;
    __testAugmentVitest_87485789cd03.expect(opts).toBeDefined();
    __testAugmentVitest_87485789cd03.expect(opts.ignoreInitial).toBe(true);
    __testAugmentVitest_87485789cd03.expect(opts.persistent).toBe(false);
    __testAugmentVitest_87485789cd03.expect(typeof opts.ignored).toBe('function');

    // the ignored function should match typical .git paths
    __testAugmentVitest_87485789cd03.expect(opts.ignored('/a/.git')).toBe(true);
    __testAugmentVitest_87485789cd03.expect(opts.ignored('foo/.git/bar')).toBe(true);

    // default debounce should be present on the service
    __testAugmentVitest_87485789cd03.expect((svc as any).debounceMs).toBe(200);

    // cleanup global slot
    delete (globalThis as any).__TEST_LAST_FS_OPTS;
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
