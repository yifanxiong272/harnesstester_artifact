import { randomBytes } from 'node:crypto';
import { mkdir, readdir, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'pathe';

import { afterEach, describe, expect, it } from 'vitest';

import { BlobStore, isBlobRef } from '../../../src/agent/records/blobref';
import type { AgentRecord } from '../../../src/agent/records';

const cleanups: string[] = [];

afterEach(async () => {
  for (const dir of cleanups.splice(0)) {
    await rm(dir, { recursive: true, force: true }).catch(() => {});
  }
});

function firstImageUrl(record: AgentRecord): string {
  return (record as unknown as { input: [{ imageUrl: { url: string } }] }).input[0].imageUrl.url;
}

async function makeStore(options?: { maxCacheSize?: number; threshold?: number }): Promise<{ store: BlobStore; blobsDir: string }> {
  const blobsDir = join(tmpdir(), `blobref-test-${randomBytes(6).toString('hex')}`);
  await mkdir(blobsDir, { recursive: true });
  cleanups.push(blobsDir);
  return {
    store: new BlobStore({
      blobsDir,
      threshold: options?.threshold ?? 4096,
      maxCacheSize: options?.maxCacheSize,
    }),
    blobsDir,
  };
}

describe('blobref', () => {












  __testAugmentVitest_620b318f4fc6.it("skip_offload_for_non_tool_result_loop_event_round_035", async () => {
    const { store } = await makeStore();
    const payload = 'X'.repeat(5000);
    const dataUri = `data:image/png;base64,${payload}`;

    // event.type is not 'tool.result' so offload must return the same record
    const part = { type: 'image_url', imageUrl: { url: dataUri } };
    const record = {
      type: 'context.append_loop_event',
      event: {
        type: 'tool.started',
        parentUuid: 'p',
        toolCallId: 'tc',
        result: { isError: false, output: [part] },
      },
    } as unknown as any;

    const off = await store.offload(record);
    __testAugmentVitest_620b318f4fc6.expect(off).toBe(record);
  });
});

import * as __testAugmentVitest_620b318f4fc6 from "vitest";

const __testAugmentLoadTarget_c1e9fc7d69a9 = async () => {
  __testAugmentVitest_620b318f4fc6.vi.doUnmock("../../../src/agent/records/blobref.js");
  __testAugmentVitest_620b318f4fc6.vi.resetModules();
  return import("../../../src/agent/records/blobref.js");
};
