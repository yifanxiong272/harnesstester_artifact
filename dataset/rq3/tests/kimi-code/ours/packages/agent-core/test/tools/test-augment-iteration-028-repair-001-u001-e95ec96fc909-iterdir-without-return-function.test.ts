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


































  __testAugmentVitest_9d026932f687.it("iterdir_without_return_function_round_028", async () => {
    // Provide an iterator object that has next() but no return() to hit the
    // branch where typeof iter.return !== 'function'. Ensure glob still runs.
    const iterdirObj: any = { next: __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue({ done: true }) };
    const iterdir = () => iterdirObj;
    const glob = __testAugmentVitest_9d026932f687.vi.fn().mockReturnValue(asyncPaths(['/workspace/a.ts']));
    const tool = new GlobTool(
      createFakeKaos({ iterdir, glob, stat: __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue(stat(1)) }),
      workspace,
    );

    const result = await executeTool(tool, context({ pattern: '*.ts' }));

    // The iterator had no return property; code must not try to call it and
    // glob must still have been invoked and produced results.
    __testAugmentVitest_9d026932f687.expect(iterdirObj.return).toBeUndefined();
    __testAugmentVitest_9d026932f687.expect(glob).toHaveBeenCalledWith('/workspace', '*.ts');
    __testAugmentVitest_9d026932f687.expect(result.output).toContain('a.ts');
  });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
