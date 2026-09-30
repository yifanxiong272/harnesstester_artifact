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


































  __testAugmentVitest_9d026932f687.it("resolveExecution_exposes_approvalRule_and_description_round_028_pass_03", async () => {
    // Directly call resolveExecution and assert the returned object contains
    // the approvalRule and a textual description that matches the pattern.
    const tool = new GlobTool(createFakeKaos(), workspace);
    const exec = tool.resolveExecution({ pattern: '*.ts' });

    __testAugmentVitest_9d026932f687.expect(exec).toHaveProperty('approvalRule');
    __testAugmentVitest_9d026932f687.expect(exec).toHaveProperty('matchesRule');
    __testAugmentVitest_9d026932f687.expect(exec.description).toBe('Searching *.ts');
    __testAugmentVitest_9d026932f687.expect(exec.display).toBeDefined();
    __testAugmentVitest_9d026932f687.expect(exec.accesses).toBeDefined();
  });
});

import * as __testAugmentVitest_9d026932f687 from "vitest";

const __testAugmentLoadTarget_9be810927370 = async () => {
  __testAugmentVitest_9d026932f687.vi.doUnmock("../../src/tools/builtin/file/glob.js");
  __testAugmentVitest_9d026932f687.vi.resetModules();
  return import("../../src/tools/builtin/file/glob.js");
};
