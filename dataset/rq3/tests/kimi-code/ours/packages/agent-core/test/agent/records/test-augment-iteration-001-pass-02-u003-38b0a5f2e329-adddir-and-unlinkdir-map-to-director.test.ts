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











  __testAugmentVitest_87485789cd03.it("adddir_and_unlinkdir_map_to_directory_kind_round_001_pass_02", async () => {
    const vi = __testAugmentVitest_87485789cd03.vi;
    const expect = __testAugmentVitest_87485789cd03.expect;

    vi.useFakeTimers();
    const listeners = new Map<string, (...args: any[]) => void>();
    const fakeWatcher = {
      add: vi.fn(),
      unwatch: vi.fn(),
      on: vi.fn((ev: string, cb: (...args: any[]) => void) => listeners.set(ev, cb)),
      close: vi.fn(() => Promise.resolve()),
    } as unknown as import('chokidar').FSWatcher;

    const sent: any[] = [];
    const lookup = { resolve: (_id: string) => ({ send: (frame: unknown) => sent.push(frame) }) } as any;
    const logger = { warn: vi.fn(), debug: vi.fn() } as any;
    const sessionService = {} as any;

    const { FsWatcherService } = await __testAugmentLoadTarget_cd1877b8e188();

    const svc = new FsWatcherService(lookup, { debounceMs: 10, watcherFactory: () => fakeWatcher as any }, logger, sessionService);

    const dir = '/root/some/dir';
    svc.addPaths('sess-dir', 'conn-dir', [dir]);

    const allCb = listeners.get('all')!;
    // addDir -> created + directory
    allCb('addDir', dir);
    vi.advanceTimersByTime(20);

    // unlinkDir -> deleted + directory
    allCb('unlinkDir', dir);
    vi.advanceTimersByTime(20);
    vi.useRealTimers();

    // Two frames expected (one per flush). Verify their payloads contain directory-kind changes
    expect(sent.length).toBeGreaterThanOrEqual(1);
    // Find any change entries with kind 'directory'
    const anyDir = sent.flatMap((f: any) => f.payload?.changes ?? []).find((c: any) => c.kind === 'directory');
    expect(anyDir).toBeDefined();
    // Ensure we saw created or deleted for directory events
    const kinds = sent.flatMap((f: any) => f.payload?.changes ?? []).map((c: any) => c.change);
    expect(kinds).toEqual(expect.arrayContaining(['created', 'deleted']));
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
