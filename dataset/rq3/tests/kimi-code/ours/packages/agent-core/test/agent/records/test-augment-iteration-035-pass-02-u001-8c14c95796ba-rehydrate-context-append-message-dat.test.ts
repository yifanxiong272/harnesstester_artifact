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












  __testAugmentVitest_620b318f4fc6.it("rehydrate_context_append_message_datauri_round_035_pass_02", async () => {
    const { store } = await makeStore();
    const payload = 'G'.repeat(5000);
    const dataUri = `data:image/png;base64,${payload}`;

    // Produce a blobref by offloading a prompt record
    const initial: any = {
      type: 'turn.prompt',
      input: [{ type: 'image_url', imageUrl: { url: dataUri } }],
      origin: { kind: 'user' },
    };

    const off = await store.offload(initial);
    const blobref = (off as any).input[0].imageUrl.url as string;
    __testAugmentVitest_620b318f4fc6.expect(blobref.startsWith('blobref:')).toBe(true);

    // Now craft a context.append_message that references that blobref and rehydrate it
    const msgRecord: any = {
      type: 'context.append_message',
      message: { content: [{ type: 'image_url', imageUrl: { url: blobref } }] },
    };

    await store.rehydrate(msgRecord);

    const url = msgRecord.message.content[0].imageUrl.url as string;
    __testAugmentVitest_620b318f4fc6.expect(url).toBe(dataUri);
  });
});

import * as __testAugmentVitest_620b318f4fc6 from "vitest";

const __testAugmentLoadTarget_c1e9fc7d69a9 = async () => {
  __testAugmentVitest_620b318f4fc6.vi.doUnmock("../../../src/agent/records/blobref.js");
  __testAugmentVitest_620b318f4fc6.vi.resetModules();
  return import("../../../src/agent/records/blobref.js");
};
