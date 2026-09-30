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


































  __testAugmentVitest_9d026932f687.it("execution_catch_handles_ENOTDIR_round_028", async () => {
    // Cause kaos.glob (during the for-await) to throw an object with code 'ENOTDIR'
    // so the execution-level catch returns the 'is not a directory' error.
    const err = Object.assign(new Error('ENOTDIR'), { code: 'ENOTDIR' });
    async function* throwingGlob() {
      throw err;
    }

    const kaos = createFakeKaos({ glob: () => throwingGlob(), stat: __testAugmentVitest_9d026932f687.vi.fn() });
    const tool = new GlobTool(kaos, workspace);

    const result = await executeTool(tool, context({ pattern: '*.py' }));

    __testAugmentVitest_9d026932f687.expect(result).toMatchObject({ isError: true });
    // The search root defaults to workspace.workspaceDir, so message should
    // mention that root "is not a directory".
    __testAugmentVitest_9d026932f687.expect(String(result.output)).toContain('/workspace is not a directory');
  });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
