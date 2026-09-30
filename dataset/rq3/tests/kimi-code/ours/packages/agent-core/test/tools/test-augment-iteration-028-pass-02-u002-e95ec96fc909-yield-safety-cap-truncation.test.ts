import { describe, expect, it, vi } from 'vitest';

import { expandBraces, type GlobInput, GlobInputSchema, GlobTool, MAX_MATCHES } from '../../src/tools/builtin/file/glob';
import type { WorkspaceConfig } from '../../src/tools/support/workspace';
import { createFakeKaos } from './fixtures/fake-kaos';
import { executeTool } from './fixtures/execute-tool';

const signal = new AbortController().signal;
const workspace: WorkspaceConfig = { workspaceDir: '/workspace', additionalDirs: ['/extra'] };

async function* asyncPaths(paths: readonly string[]) {
  for (const item of paths) yield item;
}

function stat(mtime: number, mode = 0o100000) {
  return { stMtime: mtime, stMode: mode };
}

function context(args: GlobInput) {
  return { turnId: '0', toolCallId: 'call_glob', args, signal };
}

describe('GlobTool', () => {


































  __testAugmentVitest_9d026932f687.it("yield_safety_cap_truncation_round_028_pass_02", async () => {
    // Force the kaos.glob stream to yield many items so yielded >= YIELD_SAFETY_CAP
    // with a single subPattern (subPatterns.length = 1). YIELD_SAFETY_CAP = MAX_MATCHES*2
    const bigCount = MAX_MATCHES * 2; // 200 by default
    const paths = Array.from({ length: bigCount }, (_, i) => `/workspace/_gen_${String(i)}.ts`);
    const glob = __testAugmentVitest_9d026932f687.vi.fn().mockReturnValue(asyncPaths(paths));

    const tool = new GlobTool(
      createFakeKaos({ glob, stat: __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue(stat(1)) }),
      { workspaceDir: '/workspace', additionalDirs: [] },
    );

    const result = await executeTool(tool, context({ pattern: '**' }));

    __testAugmentVitest_9d026932f687.expect(result.isError).toBeFalsy();
    const out = typeof result.output === 'string' ? result.output : '';
    // The truncation header must appear when the YIELD_SAFETY_CAP is hit.
    __testAugmentVitest_9d026932f687.expect(out).toContain(`[Truncated at ${String(MAX_MATCHES)} matches`);
  });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
