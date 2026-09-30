import type { ToolCall } from '@moonshot-ai/kosong';
import { describe, expect, it, vi } from 'vitest';

import { HookEngine } from '../../src/session/hooks';
import type { SessionSubagentHost } from '../../src/session/subagent-host';
import { FLAG_DEFINITIONS, FlagResolver } from '../../src/flags';
import { createFakeKaos } from '../tools/fixtures/fake-kaos';
import { createCommandKaos, testAgent } from './harness/agent';
import { executeTool } from '../tools/fixtures/execute-tool';

const signal = new AbortController().signal;

describe('Agent tools', () => {








  __testAugmentVitest_09a493ada127.it("runToolCallBatch_validator_compile_failure_round_004_pass_03", async () => {
    // Mock the args-validator to throw during compilation so validateExecutableToolArgs returns the compile error
    __testAugmentVitest_09a493ada127.vi.doMock('../../src/tools/args-validator', () => ({
      compileToolArgsValidator: () => { throw new Error('compile failure'); },
      validateToolArgs: () => null,
    }));

    const mod = await __testAugmentLoadTarget_7d1a7769c52d();
    const { runToolCallBatch } = mod as any;

    const events: any[] = [];
    const step = {
      dispatchEvent: async (e: any) => events.push(e),
      llm: {},
      signal: new AbortController().signal,
      turnId: 't-compile-fail',
      currentStep: 1,
      stepUuid: 's-compile-fail',
      // tool with parameters triggers compile path
      tools: [{ name: 'VTool', parameters: { type: 'object' } }],
    } as any;

    const response = { toolCalls: [{ type: 'function', id: 'call_v', name: 'VTool', arguments: '{}' }] } as any;
    const res = await runToolCallBatch(step, response);

    __testAugmentVitest_09a493ada127.expect(res.stopTurn).toBe(false);
    __testAugmentVitest_09a493ada127.expect(events.some((e) => e.type === 'tool.call')).toBe(true);
    const resultEvt = events.find((e) => e.type === 'tool.result');
    __testAugmentVitest_09a493ada127.expect(resultEvt).toBeDefined();
    // The compile error message should be propagated into the rejection output
    __testAugmentVitest_09a493ada127.expect(String(resultEvt.result.output)).toContain('compile failure');
  });
});

function bashCall(): ToolCall {
  return {
    type: 'function',
    id: 'call_bash',
    name: 'Bash',
    arguments: '{"command":"printf hook-output","timeout":60}',
  };
}

function agentCall(): ToolCall {
  return {
    type: 'function',
    id: 'call_agent',
    name: 'Agent',
    arguments: JSON.stringify({
        prompt: 'Investigate deeply',
        description: 'Investigate deeply',
        subagent_type: 'coder',
      }),
  };
}

function hookErrorMessageAssertCommand(expected: string): string {
  const script = [
    "let input = '';",
    "process.stdin.on('data', (chunk) => { input += chunk; });",
    "process.stdin.on('end', () => {",
    '  const payload = JSON.parse(input);',
    `  if (payload.error?.message === ${JSON.stringify(expected)}) process.exit(0);`,
    "  console.error(payload.error?.message ?? '<missing>');",
    '  process.exit(2);',
    '});',
  ].join('');
  return `node -e ${JSON.stringify(script)}`;
}

import * as __testAugmentVitest_09a493ada127 from "vitest";

const __testAugmentLoadTarget_7d1a7769c52d = async () => {
  __testAugmentVitest_09a493ada127.vi.doUnmock("../../src/loop/tool-call.js");
  __testAugmentVitest_09a493ada127.vi.resetModules();
  return import("../../src/loop/tool-call.js");
};
