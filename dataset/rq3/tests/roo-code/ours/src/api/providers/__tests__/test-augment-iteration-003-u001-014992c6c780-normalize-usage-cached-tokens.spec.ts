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








  __testAugmentVitest_a6a96b7a36c6.it("normalize_usage_cached_tokens_round_003", async () => {
  	__testAugmentVitest_a6a96b7a36c6.vi.restoreAllMocks()

  	const mockOptions: any = { apiModelId: "gpt-5.2-2025-12-11" }
  	const handler = new OpenAiCodexHandler(mockOptions)

  	// OAuth mocked
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("token-x")
  	__testAugmentVitest_a6a96b7a36c6.vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct-x")

  	// Preferred SDK streaming path: yield a completed event with usage that omits top-level input tokens
  	;(handler as any).client = {
  		responses: {
  			create: __testAugmentVitest_a6a96b7a36c6.vi.fn().mockResolvedValue({
  				async *[Symbol.asyncIterator]() {
  					yield {
  						type: "response.completed",
  						response: {
  							id: "u1",
  							output: [],
  							usage: {
  								// No input_tokens provided; provide prompt_tokens_details instead
  								prompt_tokens_details: { cached_tokens: 2, cache_miss_tokens: 3 },
  								output_tokens: 7,
  								cache_write_tokens: 1,
  								cache_read_tokens: 2,
  							},
  						},
  					}
  				},
  			}),
  		},
  	}

  	const stream = handler.createMessage("system", [{ role: "user", content: "hi" } as any], { taskId: "t1", tools: [] })

  	const chunks: any[] = []
  	for await (const c of stream) {
  		chunks.push(c)
  	}

  	const usageChunks = chunks.filter((c) => c?.type === "usage")
  	__testAugmentVitest_a6a96b7a36c6.expect(usageChunks.length).toBeGreaterThan(0)
  	const usage = usageChunks[0]
  	// input tokens should be cached_tokens + cache_miss_tokens
  	__testAugmentVitest_a6a96b7a36c6.expect(usage.inputTokens).toBe(5)
  	__testAugmentVitest_a6a96b7a36c6.expect(usage.outputTokens).toBe(7)
  	// subscription-based: totalCost must be 0
  	__testAugmentVitest_a6a96b7a36c6.expect(usage.totalCost).toBe(0)
  })
})

import * as __testAugmentVitest_a6a96b7a36c6 from "vitest";

const __testAugmentLoadTarget_b8dbf5116dac = async () => {
  __testAugmentVitest_a6a96b7a36c6.vi.doUnmock("../openai-codex.js");
  __testAugmentVitest_a6a96b7a36c6.vi.resetModules();
  return import("../openai-codex.js");
};
