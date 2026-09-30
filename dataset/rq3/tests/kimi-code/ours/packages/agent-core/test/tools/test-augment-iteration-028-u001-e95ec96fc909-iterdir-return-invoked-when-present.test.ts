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


































  __testAugmentVitest_9d026932f687.it("calls_iterdir_return_when_present_round_028", async () => { const iter = { next: __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue({ done: true }), return: __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue(undefined) }; const glob = __testAugmentVitest_9d026932f687.vi.fn().mockReturnValue(asyncPaths(['/workspace/a.ts'])); const kaos = createFakeKaos({ iterdir: () => iter, glob, stat: __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue(stat(1)) }); const tool = new GlobTool(kaos, workspace); const result = await executeTool(tool, context({ pattern: '*.ts' })); __testAugmentVitest_9d026932f687.expect(iter.return).toHaveBeenCalled(); __testAugmentVitest_9d026932f687.expect(result.output).toContain('a.ts'); });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
