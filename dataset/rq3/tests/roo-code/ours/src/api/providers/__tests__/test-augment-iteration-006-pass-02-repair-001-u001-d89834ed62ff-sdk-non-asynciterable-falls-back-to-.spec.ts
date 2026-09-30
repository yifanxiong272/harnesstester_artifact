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





  __testAugmentVitest_457083e09373.it("sdk_non_asynciterable_falls_back_to_fetch_round_006_pass_02", async () => {
  	// Arrange: make SDK return a plain object (no async iterator) so executeRequest falls back to fetch
  	mockResponsesCreate.mockResolvedValue({ notAnAsyncIterable: true })

  	const mockFetch = __testAugmentVitest_457083e09373.vi.fn().mockResolvedValue({
  		ok: true,
  		body: new ReadableStream({
  			start(controller) {
  				controller.enqueue(
  					new TextEncoder().encode('data: {"type":"response.text.delta","delta":"FromSDKFallback"}\n\n'),
  				)
  				controller.enqueue(new TextEncoder().encode('data: {"type":"response.done","response":{}}\n\n'))
  				controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'))
  				controller.close()
  			},
  		}),
  	})
  	global.fetch = mockFetch as any

  	// Act
  	const stream = handler.createMessage("System prompt", [{ role: "user", content: "Hi" }])
  	const chunks: any[] = []
  	for await (const c of stream) {
  		chunks.push(c)
  	}

  	// Assert: fallback produced text chunk from the SSE body
  	__testAugmentVitest_457083e09373.expect(chunks.some((ch) => ch.type === "text" && ch.text.includes("FromSDKFallback"))).toBe(true)
  	__testAugmentVitest_457083e09373.expect(mockFetch).toHaveBeenCalled()
  })
})

// Additional tests for GPT-5 streaming event coverage

import * as __testAugmentVitest_457083e09373 from "vitest";

const __testAugmentLoadTarget_9acec0937018 = async () => {
  __testAugmentVitest_457083e09373.vi.doUnmock("../openai-native.js");
  __testAugmentVitest_457083e09373.vi.resetModules();
  return import("../openai-native.js");
};
