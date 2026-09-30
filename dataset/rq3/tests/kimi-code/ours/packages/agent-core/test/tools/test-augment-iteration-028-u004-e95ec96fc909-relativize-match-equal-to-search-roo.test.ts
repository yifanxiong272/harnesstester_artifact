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


































  __testAugmentVitest_9d026932f687.it("relativizes_root_match_to_dot_round_028", async () => { const glob = __testAugmentVitest_9d026932f687.vi.fn().mockReturnValue(asyncPaths(['/workspace'])); const kaos = createFakeKaos({ glob, stat: __testAugmentVitest_9d026932f687.vi.fn().mockResolvedValue(stat(5, 0o040000)) }); const tool = new GlobTool(kaos, workspace); const result = await executeTool(tool, context({ pattern: '*' })); __testAugmentVitest_9d026932f687.expect(result.isError).toBeFalsy(); __testAugmentVitest_9d026932f687.expect(result.output).toContain('.'); });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
