// cd src && npx vitest run api/providers/__tests__/openai-codex-native-tool-calls.spec.ts

import { beforeEach, describe, expect, it, vi } from "vitest"

import { OpenAiCodexHandler } from "../openai-codex"
import type { ApiHandlerOptions } from "../../../shared/api"
import { NativeToolCallParser } from "../../../core/assistant-message/NativeToolCallParser"
import { openAiCodexOAuthManager } from "../../../integrations/openai-codex/oauth"

describe("OpenAiCodexHandler native tool calls", () => {
	let handler: OpenAiCodexHandler
	let mockOptions: ApiHandlerOptions

	beforeEach(() => {
		vi.restoreAllMocks()
		NativeToolCallParser.clearRawChunkState()
		NativeToolCallParser.clearAllStreamingToolCalls()

		mockOptions = {
			apiModelId: "gpt-5.2-2025-12-11",
			// minimal settings; OAuth is mocked below
		}
		handler = new OpenAiCodexHandler(mockOptions)
	})








  __testAugmentVitest_a6a96b7a36c6.it("pending_tool_identity_allows_arguments_round_003", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("test-token")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_test")

  	;(handler as any).client = {
  		responses: {
  			create: __testAugmentVitest_a6a96b7a36c6.vi.fn().mockResolvedValue({
  				async *[Symbol.asyncIterator]() {
  					// First, an output_item.added that sets pendingToolCallId/name
  					yield { type: "response.output_item.added", item: { type: "function_call", call_id: "callX", name: "do_it" } }
  					// Then a function_call_arguments.delta without id/name — should be attributed to pending
  					yield { type: "response.function_call_arguments.delta", delta: '{"a":1}', index: 2 }
  					yield { type: "response.completed", response: { id: "r_tool_1", status: "completed", output: [], usage: { input_tokens: 1, output_tokens: 0 } } }
  				},
  			}),
  		},
  	}

  	const stream = handler.createMessage("system", [{ role: "user", content: "call tool" } as any], { taskId: "t", tools: [] })
  	const chunks: any[] = []
  	for await (const c of stream) chunks.push(c)

  	const partials = chunks.filter((c) => c.type === "tool_call_partial")
  	__testAugmentVitest_a6a96b7a36c6.expect(partials.length).toBeGreaterThan(0)
  	__testAugmentVitest_a6a96b7a36c6.expect(partials[0]).toMatchObject({ id: "callX", name: "do_it", index: 2 })
  	__testAugmentVitest_a6a96b7a36c6.expect(partials[0].arguments).toBe('{"a":1}')
  });
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
