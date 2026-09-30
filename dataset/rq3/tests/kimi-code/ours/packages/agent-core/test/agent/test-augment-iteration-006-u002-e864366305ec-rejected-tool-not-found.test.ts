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








  __testAugmentVitest_09a493ada127.it("runToolCallBatch_rejected_tool_not_found_round_006", async () => {
    const { runToolCallBatch } = __testAugmentTarget_7d1a7769c52d;
    const events: any[] = [];
    const step = {
      dispatchEvent: async (e: any) => { events.push(e); },
      llm: {},
      signal: new AbortController().signal,
      turnId: 'turn-missing',
      currentStep: 1,
      stepUuid: 'step-missing',
    } as any;

    const response = {
      toolCalls: [ { type: 'function', id: 'call_missing', name: 'MissingTool', arguments: null } ],
    } as any;

    const result = await runToolCallBatch(step, response);

    // Should complete without stopping the turn for a single missing-tool call
    __testAugmentVitest_09a493ada127.expect(result.stopTurn).toBe(false);

    // Two events are expected: the recorded tool.call and the terminal tool.result
    __testAugmentVitest_09a493ada127.expect(events.length).toBeGreaterThanOrEqual(2);
    __testAugmentVitest_09a493ada127.expect(events[0]).toMatchObject({ type: 'tool.call', uuid: 'call_missing', toolCallId: 'call_missing', name: 'MissingTool' });

    const toolResultEvent = events.find((e) => e.type === 'tool.result');
    __testAugmentVitest_09a493ada127.expect(toolResultEvent).toBeTruthy();
    __testAugmentVitest_09a493ada127.expect(toolResultEvent.result).toMatchObject({ isError: true });
    __testAugmentVitest_09a493ada127.expect(String(toolResultEvent.result.output)).toContain('Tool "MissingTool" not found');
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
