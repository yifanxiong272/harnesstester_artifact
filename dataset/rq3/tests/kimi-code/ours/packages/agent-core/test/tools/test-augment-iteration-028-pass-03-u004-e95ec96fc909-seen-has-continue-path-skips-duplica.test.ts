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


































  __testAugmentVitest_9d026932f687.it("seen_has_continue_path_skips_duplicate_push_round_028_pass_03", async () => {
    // Ensure the code path where a duplicate yield is seen and the loop continues
    // (the `if (seen.has(filePath)) continue` branch) executes.
    // First yield a path twice and then a distinct path so seen.has is exercised.
    async function* mixedGen() {
      yield '/workspace/dup.ts';
      yield '/workspace/dup.ts';
      yield '/workspace/unique.ts';
    }

    const glob = __testAugmentVitest_9d026932f687.vi.fn().mockReturnValue(mixedGen());
    const statMock = __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue(stat(1));
    const tool = new GlobTool(createFakeKaos({ glob, stat: statMock }), workspace);

    const result = await executeTool(tool, context({ pattern: '*.ts' }));

    __testAugmentVitest_9d026932f687.expect(result.isError).toBeFalsy();
    const out = typeof result.output === 'string' ? result.output : '';
    const lines = out.split('\n').filter(Boolean);
    // Both unique.ts and dup.ts should appear, but dup.ts only once (duplicate skipped)
    __testAugmentVitest_9d026932f687.expect(lines).toContain('dup.ts');
    __testAugmentVitest_9d026932f687.expect(lines.filter((l) => l === 'dup.ts').length).toBe(1);
    __testAugmentVitest_9d026932f687.expect(lines).toContain('unique.ts');
  });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
