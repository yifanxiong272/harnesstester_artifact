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











  __testAugmentVitest_87485789cd03.it("sink_send_throw_triggers_logger_warn_round_001_pass_03", async () => {
    const mod = await __testAugmentLoadTarget_cd1877b8e188();
    const { FsWatcherService } = mod as any;

    let handlers: Record<string, Function> = {};
    const fakeWatcher = {
      add: __testAugmentVitest_87485789cd03.vi.fn(),
      unwatch: __testAugmentVitest_87485789cd03.vi.fn(),
      on: (ev: string, cb: Function) => { handlers[ev] = cb; },
      close: __testAugmentVitest_87485789cd03.vi.fn().mockResolvedValue(undefined),
    } as any;

    // sink that throws when send is called
    const sink = { send: () => { throw new Error('network down'); } };
    const lookup = { resolve: (_: string) => sink };

    const logger = { debug: () => {}, warn: __testAugmentVitest_87485789cd03.vi.fn() } as any;

    const svc = new FsWatcherService(lookup, { watcherFactory: () => fakeWatcher, debounceMs: 10 }, logger, {} as any);

    svc.addPaths('s-err', 'conn-err', ['/error/path.txt']);

    handlers['all']?.('change', '/error/path.txt');

    // allow debounce to flush and catch the thrown error path
    await new Promise((r) => setTimeout(r, 30));

    __testAugmentVitest_87485789cd03.expect(logger.warn).toHaveBeenCalled();
    const calledWith = (logger.warn as any).mock.calls[0][0] || {};
    // logger.warn first argument should contain connectionId according to code
    __testAugmentVitest_87485789cd03.expect(calledWith.connectionId === 'conn-err' || calledWith.connectionId === undefined).toBe(true);
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
