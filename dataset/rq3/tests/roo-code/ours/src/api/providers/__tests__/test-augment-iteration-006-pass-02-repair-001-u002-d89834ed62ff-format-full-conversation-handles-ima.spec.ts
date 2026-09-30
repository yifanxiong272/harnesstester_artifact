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





  __testAugmentVitest_457083e09373.it("format_full_conversation_handles_image_and_tool_result_round_006_pass_02", async () => {
  	// Ensure SDK path fails so makeResponsesApiRequest (fetch) is used and we can capture the request body
  	mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

  	const mockFetch = __testAugmentVitest_457083e09373.vi.fn().mockResolvedValue({
  		ok: true,
  		body: new ReadableStream({
  			start(controller) {
  				controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n'))
  				controller.close()
  			},
  		}),
  	})
  	global.fetch = mockFetch as any

  	// Build a user message with image and tool_result blocks
  	const imageBlock = { type: "image", source: { media_type: "image/png", data: "aGVsbG8=" } }
  	const toolResultBlock = { type: "tool_result", tool_use_id: "tool--use-123", content: "tool-output" }
  	const messages = [{ role: "user", content: [imageBlock, toolResultBlock] }]

  	const stream = handler.createMessage("System prompt", messages)
  	for await (const _ of stream) {
  		// drain
  	}

  	__testAugmentVitest_457083e09373.expect(mockFetch).toHaveBeenCalled()
  	const callBody = JSON.parse(mockFetch.mock.calls[0][1].body as string)
  	// The first input item should be the user message containing an input_image
  	__testAugmentVitest_457083e09373.expect(Array.isArray(callBody.input)).toBe(true)
  	const first = callBody.input[0]
  	__testAugmentVitest_457083e09373.expect(first.role).toBe("user")
  	__testAugmentVitest_457083e09373.expect(Array.isArray(first.content)).toBe(true)
  	__testAugmentVitest_457083e09373.expect(first.content.some((c: any) => c.type === "input_image" && c.image_url.startsWith("data:image/png;base64,"))).toBe(true)

  	// The tool result should be emitted as a top-level function_call_output item
  	const hasToolOutput = callBody.input.some((it: any) => it.type === "function_call_output" && it.output && it.call_id)
  	__testAugmentVitest_457083e09373.expect(hasToolOutput).toBe(true)
  })
})

// Additional tests for GPT-5 streaming event coverage

import * as __testAugmentVitest_457083e09373 from "vitest";

const __testAugmentLoadTarget_9acec0937018 = async () => {
  __testAugmentVitest_457083e09373.vi.doUnmock("../openai-native.js");
  __testAugmentVitest_457083e09373.vi.resetModules();
  return import("../openai-native.js");
};
