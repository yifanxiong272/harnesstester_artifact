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











  __testAugmentVitest_87485789cd03.it("ignore_unknown_chokidar_event_round_001_pass_02", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    // capture event handler
    let handlers: Record<string, Function> = {};
    const fakeWatcher = {
      add: __testAugmentVitest_87485789cd03.vi.fn(),
      unwatch: __testAugmentVitest_87485789cd03.vi.fn(),
      on: (ev: string, cb: Function) => { handlers[ev] = cb; },
      close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined),
    } as any;

    const sent: any[] = [];
    const sink = { send: (frame: any) => sent.push(frame) };
    const lookup = { resolve: (_id: string) => sink };
    const logger = { debug: () => {}, warn: () => {} } as any;

    const svc = new FsWatcherService(lookup, { watcherFactory: () => fakeWatcher, debounceMs: 10 }, logger, {} as any);

    const sessionId = 's-unk';
    const connectionId = 'c-unk';
    svc.addPaths(sessionId, connectionId, ['/root/unk/file.txt']);

    // send an unknown event that mapChokidarEventToAction will map to undefined
    handlers['all']?.('renamed-event', '/root/unk/file.txt');

    // give a short delay for any timers (should be none)
    await new Promise((r) => setTimeout(r, 20));

    __testAugmentVitest_87485789cd03.expect(sent).toHaveLength(0);
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
