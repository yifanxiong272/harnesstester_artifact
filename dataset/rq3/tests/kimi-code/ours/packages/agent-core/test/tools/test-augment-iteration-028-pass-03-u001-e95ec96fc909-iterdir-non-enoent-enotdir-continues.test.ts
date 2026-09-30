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


































  __testAugmentVitest_9d026932f687.it("iterdir_non_ENOENT_ENOTDIR_continues_to_glob_round_028_pass_03", async () => {
    // iterdir throws an error object that has a `code` property which is
    // neither ENOENT nor ENOTDIR. The pre-check should fall through and
    // let kaos.glob run.
    const iterdir = async function* () {
      await Promise.resolve();
      throw Object.assign(new Error('EACCES: permission denied'), { code: 'EACCES' });
      // satisfy generator shape
      // eslint-disable-next-line no-unreachable
      yield '';
    };

    const glob = __testAugmentVitest_9d026932f687.vi.fn().mockReturnValue(asyncPaths(['/workspace/allowed.ts']));
    const tool = new GlobTool(createFakeKaos({ iterdir, glob, stat: __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue(stat(1)) }), workspace);

    const result = await executeTool(tool, context({ pattern: '*.ts' }));

    __testAugmentVitest_9d026932f687.expect(glob).toHaveBeenCalledWith('/workspace', '*.ts');
    __testAugmentVitest_9d026932f687.expect(result.isError).toBeFalsy();
    __testAugmentVitest_9d026932f687.expect(String(result.output)).toContain('allowed.ts');
  });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
