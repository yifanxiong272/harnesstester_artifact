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








  __testAugmentVitest_09a493ada127.it("runToolCallBatch_prepare_aborted_round_004_pass_02", async () => {
    const { runToolCallBatch } = __testAugmentTarget_7d1a7769c52d;
    const events: any[] = [];

    // Aborted signal before prepareToolCall resolves -> settleAborted path
    const ac = new AbortController();
    ac.abort();

    const step = {
      dispatchEvent: async (e: any) => events.push(e),
      llm: {},
      signal: ac.signal,
      turnId: 't-abort-prepare',
      currentStep: 1,
      stepUuid: 's-abort-prepare',
      // provide a simple tool so preflight finds it and validation compiles
      tools: [
        {
          name: 'AbortTool',
          parameters: { type: 'object' },
          // resolveExecution will succeed but prepareToolCall should see signal.aborted after that
          resolveExecution: async () => ({
            isError: false,
            accesses: undefined,
            execute: async () => ({ output: 'should-not-run' }),
          }),
        },
      ],
    } as any;

    const response = { toolCalls: [{ type: 'function', id: 'call_abort', name: 'AbortTool', arguments: null }] } as any;
    const res = await runToolCallBatch(step, response);

    __testAugmentVitest_09a493ada127.expect(res.stopTurn).toBe(false);
    // There should be a tool.call and a tool.result; the result output should mention aborted
    __testAugmentVitest_09a493ada127.expect(events.some((e) => e.type === 'tool.call')).toBe(true);
    const resultEvt = events.find((e) => e.type === 'tool.result');
    __testAugmentVitest_09a493ada127.expect(resultEvt).toBeDefined();
    __testAugmentVitest_09a493ada127.expect(String(resultEvt.result.output)).toContain('was aborted');
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
