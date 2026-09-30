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








  __testAugmentVitest_09a493ada127.it("runToolCallBatch_coerce_primitive_round_004_pass_02", async () => {
    const { runToolCallBatch } = __testAugmentTarget_7d1a7769c52d;
    const events: any[] = [];

    const step = {
      dispatchEvent: async (e: any) => events.push(e),
      llm: {},
      signal: new AbortController().signal,
      turnId: 't-coerce-prim',
      currentStep: 1,
      stepUuid: 's-coerce-prim',
      tools: [
        {
          name: 'PrimTool',
          parameters: { type: 'object' },
          resolveExecution: async () => ({
            isError: false,
            accesses: undefined,
            // execute resolves to a primitive to trigger the primitive branch
            execute: async () => 123,
          }),
        },
      ],
    } as any;

    const response = { toolCalls: [{ type: 'function', id: 'call_prim', name: 'PrimTool', arguments: null }] } as any;
    const res = await runToolCallBatch(step, response);

    __testAugmentVitest_09a493ada127.expect(res.stopTurn).toBe(false);
    __testAugmentVitest_09a493ada127.expect(events.some((e) => e.type === 'tool.call')).toBe(true);
    const resultEvt = events.find((e) => e.type === 'tool.result');
    __testAugmentVitest_09a493ada127.expect(resultEvt).toBeDefined();
    __testAugmentVitest_09a493ada127.expect(String(resultEvt.result.output)).toContain('returned a number instead of a tool result');
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
