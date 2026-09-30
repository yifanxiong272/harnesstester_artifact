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








  __testAugmentVitest_a6a96b7a36c6.it("normalizeUsage_sums_cached_and_cacheMiss_round_003", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("test-token")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_test")

  	// Simulate SDK async iterable returning a completed response with input_tokens = 0 but input_tokens_details present
  	;(handler as any).client = {
  		responses: {
  			create: __testAugmentVitest_a6a96b7a36c6.vi.fn().mockResolvedValue({
  				async *[Symbol.asyncIterator]() {
  					yield {
  						type: "response.completed",
  						response: {
  							id: "resp_usage_1",
  							status: "completed",
  							output: [],
  							usage: {
  								input_tokens: 0,
  								input_tokens_details: { cached_tokens: 3, cache_miss_tokens: 5 },
  								output_tokens: 2,
  							},
  						},
  					}
  				},
  			}),
  		},
  	}

  	const stream = handler.createMessage("system", [{ role: "user", content: "hello" } as any], { taskId: "t", tools: [] })
  	const chunks: any[] = []
  	for await (const c of stream) {
  		chunks.push(c)
  	}

  	const usageChunks = chunks.filter((c) => c.type === "usage")
  	__testAugmentVitest_a6a96b7a36c6.expect(usageChunks.length).toBeGreaterThan(0)
  	// cached_tokens(3)+cache_miss_tokens(5) => 8
  	__testAugmentVitest_a6a96b7a36c6.expect(usageChunks[0].inputTokens).toBe(8)
  	__testAugmentVitest_a6a96b7a36c6.expect(usageChunks[0].totalCost).toBe(0)
  });
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
