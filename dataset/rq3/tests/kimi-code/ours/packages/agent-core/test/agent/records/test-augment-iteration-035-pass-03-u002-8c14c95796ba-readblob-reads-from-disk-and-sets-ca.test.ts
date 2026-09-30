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












  __testAugmentVitest_620b318f4fc6.it("readBlob_reads_from_disk_and_sets_cache_round_035_pass_03", async () => {
    // Create a blob directory and write a file directly to it so a fresh BlobStore will have to read from disk.
    const { blobsDir } = await makeStore();
    const hash = 'disk-hash-abc123';
    const payloadBuffer = Buffer.from('disk-bytes');

    // Write the file directly to the blobsDir (simulate an existing blob on disk)
    const fs = await Promise.resolve().then(() => import('node:fs/promises'));
    await fs.writeFile(join(blobsDir, hash), payloadBuffer);

    // New BlobStore instance (empty in-memory cache) pointed at the same blobsDir should read the file from disk.
    const store2 = new (await Promise.resolve().then(() => __testAugmentTarget_c1e9fc7d69a9)).BlobStore({ blobsDir, threshold: 4096 });

    const record: any = {
      type: 'turn.prompt',
      input: [{ type: 'image_url', imageUrl: { url: `blobref:image/png;${hash}` } }],
      origin: { kind: 'user' },
    };

    await store2.rehydrate(record);

    // The file's bytes should have been read and converted to a data URI.
    const expected = `data:image/png;base64,${payloadBuffer.toString('base64')}`;
    __testAugmentVitest_620b318f4fc6.expect((record.input as any)[0].imageUrl.url).toBe(expected);
  });
});

import * as __testAugmentVitest_620b318f4fc6 from "vitest";

import * as __testAugmentTarget_c1e9fc7d69a9 from "../../../src/agent/records/blobref.js";

const __testAugmentLoadTarget_c1e9fc7d69a9 = async () => {
  __testAugmentVitest_620b318f4fc6.vi.doUnmock("../../../src/agent/records/blobref.js");
  __testAugmentVitest_620b318f4fc6.vi.resetModules();
  return import("../../../src/agent/records/blobref.js");
};
