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





  __testAugmentVitest_457083e09373.it("sdk_choices_delta_legacy_fallback_round_006_pass_03", async () => {
  	// SDK returns legacy-style choices delta content
  	const asyncIterable = {
  		async *[Symbol.asyncIterator]() {
  			yield { choices: [{ delta: { content: "legacy content" } }] }
  			yield { type: "response.done", response: {} }
  		},
  	}
  	mockResponsesCreate.mockResolvedValue(asyncIterable)

  	const chunks: any[] = []
  	for await (const c of handler.createMessage("System prompt", [{ role: "user", content: "Hi" }])) {
  		chunks.push(c)
  	}

  	const textChunk = chunks.find((ch) => ch.type === "text")
  	__testAugmentVitest_457083e09373.expect(textChunk).toBeDefined()
  	__testAugmentVitest_457083e09373.expect(textChunk.text).toBe("legacy content")
  })
})

// Additional tests for GPT-5 streaming event coverage

import * as __testAugmentVitest_457083e09373 from "vitest";

const __testAugmentLoadTarget_9acec0937018 = async () => {
  __testAugmentVitest_457083e09373.vi.doUnmock("../openai-native.js");
  __testAugmentVitest_457083e09373.vi.resetModules();
  return import("../openai-native.js");
};
