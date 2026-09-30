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


































  __testAugmentVitest_9d026932f687.it("stat_missing_stMtime_uses_default_zero_round_028", async () => {
    // Two yielded files; first stat lacks stMtime (defaults to 0), second has stMtime=5.
    // Sorting should place the higher-mtime file first.
    const glob = __testAugmentVitest_9d026932f687.vi.fn().mockReturnValue(asyncPaths(['/workspace/low.ts', '/workspace/high.ts']));
    const statMock = __testAugmentVitest_9d026932f687.vi.fn()
      .mockResolvedValueOnce({ /* no stMtime */ stMode: 0o100000 })
      .mockResolvedValueOnce({ stMtime: 5, stMode: 0o100000 });

    const tool = new GlobTool(createFakeKaos({ glob, stat: statMock }), workspace);

    const result = await executeTool(tool, context({ pattern: '*.ts' }));

    __testAugmentVitest_9d026932f687.expect(result.isError).toBeFalsy();
    const output = typeof result.output === 'string' ? result.output : '';
    const lines = output.split('\n').filter(Boolean);
    __testAugmentVitest_9d026932f687.expect(lines[0]).toContain('high.ts');
    __testAugmentVitest_9d026932f687.expect(lines[1]).toContain('low.ts');
  });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
