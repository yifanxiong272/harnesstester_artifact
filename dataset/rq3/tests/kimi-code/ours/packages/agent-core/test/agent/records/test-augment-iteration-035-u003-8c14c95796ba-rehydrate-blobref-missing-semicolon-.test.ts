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












  __testAugmentVitest_620b318f4fc6.it("rehydrate_blobref_missing_semicolon_round_035", async () => {
    const { store } = await makeStore();

    // blobref without a semicolon should be treated as missing -> placeholder
    const record = {
      type: 'turn.prompt',
      input: [{ type: 'image_url', imageUrl: { url: 'blobref:imagepnghash' } }],
      origin: { kind: 'user' },
    } as unknown as any;

    await store.rehydrate(record);

    __testAugmentVitest_620b318f4fc6.expect((record.input as any)[0].imageUrl.url).toBe('[media missing]');
  });
});

import * as __testAugmentVitest_620b318f4fc6 from "vitest";

const __testAugmentLoadTarget_c1e9fc7d69a9 = async () => {
  __testAugmentVitest_620b318f4fc6.vi.doUnmock("../../../src/agent/records/blobref.js");
  __testAugmentVitest_620b318f4fc6.vi.resetModules();
  return import("../../../src/agent/records/blobref.js");
};
