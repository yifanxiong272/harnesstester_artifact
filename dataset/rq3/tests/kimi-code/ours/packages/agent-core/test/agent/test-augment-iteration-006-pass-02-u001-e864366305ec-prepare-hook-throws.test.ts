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








  __testAugmentVitest_09a493ada127.it("runToolCallBatch_prepare_hook_throws_round_006_pass_02", async () => {
    const { runToolCallBatch } = __testAugmentTarget_7d1a7769c52d;
    const events: any[] = [];

    // Hook that throws a non-abort error to exercise the hookFailed branch
    const hooks = {
      prepareToolExecution: async () => {
        throw new Error('prepare-boom');
      },
    } as any;

    const tool = { name: 'T1', parameters: { type: 'object' } } as any;

    const step = {
      tools: [tool],
      hooks,
      dispatchEvent: async (e: any) => { events.push(e); },
      llm: {},
      signal: new AbortController().signal,
      turnId: 'turn-prepare-err',
      currentStep: 1,
      stepUuid: 'step-prepare-err',
    } as any;

    const response = { toolCalls: [{ type: 'function', id: 'c1', name: 'T1', arguments: null }] } as any;

    const result = await runToolCallBatch(step, response);

    // The batch should complete without requesting a turn stop
    __testAugmentVitest_09a493ada127.expect(result.stopTurn).toBe(false);

    // Expect a tool.call and a tool.result with a hookFailed-style message
    __testAugmentVitest_09a493ada127.expect(events.some((e) => e.type === 'tool.call' && e.uuid === 'c1')).toBe(true);
    const tr = events.find((e) => e.type === 'tool.result' && e.parentUuid === 'c1');
    __testAugmentVitest_09a493ada127.expect(tr).toBeTruthy();
    __testAugmentVitest_09a493ada127.expect(String(tr.result.output)).toContain('prepareToolExecution hook failed for "T1"');
    __testAugmentVitest_09a493ada127.expect(tr.result.isError).toBe(true);
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
