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


































  __testAugmentVitest_9d026932f687.it("relativize_returns_abs_when_candidate_not_under_base_round_028_pass_02", async () => {
    // When shouldRelativize is true (search root is the workspace), but the
    // matched path is outside that base, relativizeIfUnder should return
    // the candidate unchanged (absolute path).
    const glob = __testAugmentVitest_9d026932f687.vi.fn().mockReturnValue(asyncPaths(['/other/place/file.py']));
    const tool = new GlobTool(createFakeKaos({ glob, stat: __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue(stat(1)) }), workspace);

    const result = await executeTool(tool, context({ pattern: '*.py' }));

    __testAugmentVitest_9d026932f687.expect(result.isError).toBeFalsy();
    // The displayed path should remain absolute because the candidate is not under the base.
    __testAugmentVitest_9d026932f687.expect(String(result.output)).toContain('/other/place/file.py');
  });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
