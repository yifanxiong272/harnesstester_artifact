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











  __testAugmentVitest_87485789cd03.it("addDir_and_unlinkDir_produce_directory_kind_round_001_pass_03", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    // capture handlers so we can simulate chokidar events
    let handlers: Record<string, Function> = {};
    const fakeWatcher = {
      add: __testAugmentVitest_87485789cd03.vi.fn(),
      unwatch: __testAugmentVitest_87485789cd03.vi.fn(),
      on: (ev: string, cb: Function) => { handlers[ev] = cb; },
      close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined),
    } as any;

    const sent: any[] = [];
    const sink = { send: (frame: any) => sent.push(frame) };
    const lookup = { resolve: (_: string) => sink };
    const logger = { debug: () => {}, warn: () => {} } as any;

    const svc = new FsWatcherService(lookup, { watcherFactory: () => fakeWatcher, debounceMs: 20 }, logger, {} as any);

    const sessionId = 'sd';
    const connectionId = 'cd';
    const dirPath = '/proj/dir';
    svc.addPaths(sessionId, connectionId, [dirPath]);

    // simulate addDir -> should map to action 'created' and kind 'directory'
    handlers['all']?.('addDir', dirPath);
    // allow debounce/flush
    await new Promise((r) => setTimeout(r, 40));

    __testAugmentVitest_87485789cd03.expect(sent.length).toBeGreaterThanOrEqual(1);
    const createdFrame = sent.find((f: any) => f.payload?.changes?.length);
    __testAugmentVitest_87485789cd03.expect(createdFrame).toBeDefined();
    __testAugmentVitest_87485789cd03.expect(createdFrame.payload.changes[0].change).toBe('created');
    __testAugmentVitest_87485789cd03.expect(createdFrame.payload.changes[0].kind).toBe('directory');

    // clear sent and simulate unlinkDir -> should map to 'deleted' and 'directory'
    sent.length = 0;
    handlers['all']?.('unlinkDir', dirPath);
    await new Promise((r) => setTimeout(r, 40));

    __testAugmentVitest_87485789cd03.expect(sent.length).toBeGreaterThanOrEqual(1);
    const deletedFrame = sent.find((f: any) => f.payload?.changes?.length);
    __testAugmentVitest_87485789cd03.expect(deletedFrame.payload.changes[0].change).toBe('deleted');
    __testAugmentVitest_87485789cd03.expect(deletedFrame.payload.changes[0].kind).toBe('directory');
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
