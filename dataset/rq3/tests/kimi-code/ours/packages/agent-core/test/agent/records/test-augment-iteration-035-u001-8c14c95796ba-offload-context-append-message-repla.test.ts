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












  __testAugmentVitest_620b318f4fc6.it("offload_context_append_message_replaces_content_round_035", async () => {
    const { store, blobsDir } = await makeStore();
    const payload = 'Z'.repeat(5000);
    const dataUri = `data:image/png;base64,${payload}`;

    // original inner object must stay untouched
    const innerImageUrl = { url: dataUri };
    const part = { type: 'image_url', imageUrl: innerImageUrl };
    const record = {
      type: 'context.append_message',
      message: { content: [part] },
    } as unknown as any;

    const offloaded = await store.offload(record);

    // original record and part must remain the same references
    __testAugmentVitest_620b318f4fc6.expect(record.message.content[0]).toBe(part);
    __testAugmentVitest_620b318f4fc6.expect(part.imageUrl).toBe(innerImageUrl);
    __testAugmentVitest_620b318f4fc6.expect(innerImageUrl.url).toBe(dataUri);

    // returned record must be a new object carrying a fresh imageUrl object
    __testAugmentVitest_620b318f4fc6.expect(offloaded).not.toBe(record);
    __testAugmentVitest_620b318f4fc6.expect(offloaded.message).not.toBe(record.message);
    __testAugmentVitest_620b318f4fc6.expect(offloaded.message.content[0].imageUrl).not.toBe(innerImageUrl);
    __testAugmentVitest_620b318f4fc6.expect(typeof offloaded.message.content[0].imageUrl.url).toBe('string');
    __testAugmentVitest_620b318f4fc6.expect(offloaded.message.content[0].imageUrl.url.startsWith('blobref:image/png;')).toBe(true);

    // ensure a blob file was created on disk (sanity check)
    const files = await Promise.resolve().then(() => import('node:fs/promises')).then(m => m.readdir(blobsDir));
    __testAugmentVitest_620b318f4fc6.expect(files.length).toBeGreaterThanOrEqual(1);
  });
});

import * as __testAugmentVitest_620b318f4fc6 from "vitest";

const __testAugmentLoadTarget_c1e9fc7d69a9 = async () => {
  __testAugmentVitest_620b318f4fc6.vi.doUnmock("../../../src/agent/records/blobref.js");
  __testAugmentVitest_620b318f4fc6.vi.resetModules();
  return import("../../../src/agent/records/blobref.js");
};
