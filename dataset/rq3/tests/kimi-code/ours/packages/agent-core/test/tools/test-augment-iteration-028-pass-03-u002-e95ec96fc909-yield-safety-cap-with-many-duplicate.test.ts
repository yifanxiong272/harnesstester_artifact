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


































  __testAugmentVitest_9d026932f687.it("yield_safety_cap_with_many_duplicates_truncates_by_yielded_round_028_pass_03", async () => {
    // Produce many duplicate yields so `yielded` reaches YIELD_SAFETY_CAP while
    // `entries.length` stays small (dedup), forcing the yielded-cap truncation
    // branch (lines 224-226) to run.
    const repeats = MAX_MATCHES * 2; // YIELD_SAFETY_CAP for single subpattern
    async function* dupGen() {
      for (let i = 0; i < repeats; i++) {
        yield '/workspace/dup.ts';
      }
    }

    const glob = __testAugmentVitest_9d026932f687.vi.fn().mockReturnValue(dupGen());
    const tool = new GlobTool(
      createFakeKaos({ glob, stat: __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue(stat(1)) }),
      { workspaceDir: '/workspace', additionalDirs: [] },
    );

    const result = await executeTool(tool, context({ pattern: '**' }));

    __testAugmentVitest_9d026932f687.expect(result.isError).toBeFalsy();
    const out = typeof result.output === 'string' ? result.output : '';
    __testAugmentVitest_9d026932f687.expect(out).toContain(`[Truncated at ${String(MAX_MATCHES)} matches`);
    // Dedup ensures only one visible occurrence of the duplicated file.
    const lines = out.split('\n').filter(Boolean);
    __testAugmentVitest_9d026932f687.expect(lines.filter((l) => l.endsWith('dup.ts')).length).toBe(1);
  });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
