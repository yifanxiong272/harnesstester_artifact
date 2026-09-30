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








  __testAugmentVitest_09a493ada127.it("runToolCallBatch_authorize_hook_throws_round_006_pass_02", async () => {
    const { runToolCallBatch } = __testAugmentTarget_7d1a7769c52d;
    const events: any[] = [];

    // authorizeToolExecution throws a non-abort error; prepare hook is absent so we reach authorization
    const hooks = {
      authorizeToolExecution: async () => {
        throw new Error('auth-boom');
      },
    } as any;

    // Tool with a resolveExecution that returns a runnable execution (so authorize hook runs)
    const tool = {
      name: 'TAuth',
      parameters: { type: 'object' },
      resolveExecution: async () => ({
        isError: false,
        execute: async () => ({ output: 'should-not-run' }),
        accesses: undefined,
        stopBatchAfterThis: false,
      }),
    } as any;

    const step = {
      tools: [tool],
      hooks,
      dispatchEvent: async (e: any) => { events.push(e); },
      llm: {},
      signal: new AbortController().signal,
      turnId: 'turn-auth-err',
      currentStep: 1,
      stepUuid: 'step-auth-err',
      log: undefined,
    } as any;

    const response = { toolCalls: [{ type: 'function', id: 'c1', name: 'TAuth', arguments: null }] } as any;

    const result = await runToolCallBatch(step, response);

    __testAugmentVitest_09a493ada127.expect(result.stopTurn).toBe(false);
    __testAugmentVitest_09a493ada127.expect(events.some((e) => e.type === 'tool.call' && e.uuid === 'c1')).toBe(true);

    const tr = events.find((e) => e.type === 'tool.result' && e.parentUuid === 'c1');
    __testAugmentVitest_09a493ada127.expect(tr).toBeTruthy();
    __testAugmentVitest_09a493ada127.expect(String(tr.result.output)).toContain('authorizeToolExecution hook failed for "TAuth"');
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
