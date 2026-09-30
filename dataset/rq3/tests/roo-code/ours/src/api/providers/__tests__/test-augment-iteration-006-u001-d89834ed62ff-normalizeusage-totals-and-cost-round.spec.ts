// npx vitest run api/providers/__tests__/openai-native.spec.ts

import { Anthropic } from "@anthropic-ai/sdk"
import OpenAI from "openai"

import {} from "@roo-code/types"

import { OpenAiNativeHandler } from "../openai-native"
import { ApiHandlerOptions } from "../../../shared/api"

// Mock OpenAI client - now everything uses Responses API
const mockResponsesCreate = vitest.fn()

vitest.mock("openai", () => {
	return {
		__esModule: true,
		default: vitest.fn().mockImplementation(() => ({
			responses: {
				create: mockResponsesCreate,
			},
		})),
	}
})

describe("OpenAiNativeHandler", () => {
	let handler: OpenAiNativeHandler
	let mockOptions: ApiHandlerOptions
	const systemPrompt = "You are a helpful assistant."
	const messages: Anthropic.Messages.MessageParam[] = [
		{
			role: "user",
			content: "Hello!",
		},
	]

	beforeEach(() => {
		mockOptions = {
			apiModelId: "gpt-4.1",
			openAiNativeApiKey: "test-api-key",
		}
		handler = new OpenAiNativeHandler(mockOptions)
		mockResponsesCreate.mockClear()
		// Clear fetch mock if it exists
		if ((global as any).fetch) {
			delete (global as any).fetch
		}
	})

	afterEach(() => {
		// Clean up fetch mock
		if ((global as any).fetch) {
			delete (global as any).fetch
		}
	})





  __testAugmentVitest_457083e09373.it("normalizeUsage computes totals and cost_round_006", async () => {
  	// Use handler fixture from the seed harness
  	const model = handler.getModel()

  	const usage = {
  		// No explicit input_tokens, but detailed breakdown exists
  		input_tokens_details: { cached_tokens: 3, cache_miss_tokens: 7 },
  		// explicit output token field
  		output_tokens: 5,
  		// explicit cache write/read tokens
  		cache_creation_input_tokens: 2,
  		cache_read_input_tokens: 1,
  		// reasoning tokens within output details
  		output_tokens_details: { reasoning_tokens: 4 },
  	}

  	const out = (handler as any).normalizeUsage(usage, model)
  	__testAugmentVitest_457083e09373.expect(out).toBeDefined()
  	__testAugmentVitest_457083e09373.expect(out!.type).toBe("usage")
  	// total input tokens should be derived from cached + cache_miss
  	__testAugmentVitest_457083e09373.expect(out!.inputTokens).toBe(10)
  	__testAugmentVitest_457083e09373.expect(out!.outputTokens).toBe(5)
  	__testAugmentVitest_457083e09373.expect(out!.cacheWriteTokens).toBe(2)
  	__testAugmentVitest_457083e09373.expect(out!.cacheReadTokens).toBe(1)
  	__testAugmentVitest_457083e09373.expect(out!.reasoningTokens).toBe(4)
  	// totalCost must be provided and numeric (calculated via shared cost helper)
  	__testAugmentVitest_457083e09373.expect(typeof out!.totalCost).toBe("number")
  })
})

// Additional tests for GPT-5 streaming event coverage

import * as __testAugmentVitest_457083e09373 from "vitest";

const __testAugmentLoadTarget_9acec0937018 = async () => {
  __testAugmentVitest_457083e09373.vi.doUnmock("../openai-native.js");
  __testAugmentVitest_457083e09373.vi.resetModules();
  return import("../openai-native.js");
};
