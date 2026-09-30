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








  __testAugmentVitest_09a493ada127.it("runToolCallBatch_finalize_hook_throws_round_004_pass_03", async () => {
    const { runToolCallBatch } = __testAugmentTarget_7d1a7769c52d;
    const events: any[] = [];

    const step = {
      dispatchEvent: async (e: any) => events.push(e),
      llm: {},
      signal: new AbortController().signal,
      turnId: 't-finalize-throw',
      currentStep: 1,
      stepUuid: 's-finalize-throw',
      hooks: {
        finalizeToolResult: async () => {
          throw new Error('finalize boom');
        },
      },
      tools: [
        {
          name: 'FinTool',
          parameters: { type: 'object' },
          resolveExecution: async () => ({
            isError: false,
            accesses: undefined,
            execute: async () => ({ output: 'original' }),
          }),
        },
      ],
    } as any;

    const response = { toolCalls: [{ type: 'function', id: 'call_fin', name: 'FinTool', arguments: null }] } as any;
    const res = await runToolCallBatch(step, response);

    __testAugmentVitest_09a493ada127.expect(res.stopTurn).toBe(false);
    // The finalize hook throws, so the final result should be replaced with an error result mentioning the finalize hook failure
    const resultEvt = events.find((e) => e.type === 'tool.result');
    __testAugmentVitest_09a493ada127.expect(resultEvt).toBeDefined();
    __testAugmentVitest_09a493ada127.expect(String(resultEvt.result.output)).toContain('finalizeToolResult hook failed');
    __testAugmentVitest_09a493ada127.expect(resultEvt.result.isError).toBe(true);
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

import * as __testAugmentTarget_7d1a7769c52d from "../../src/loop/tool-call.js";

const __testAugmentLoadTarget_7d1a7769c52d = async () => {
  __testAugmentVitest_09a493ada127.vi.doUnmock("../../src/loop/tool-call.js");
  __testAugmentVitest_09a493ada127.vi.resetModules();
  return import("../../src/loop/tool-call.js");
};
