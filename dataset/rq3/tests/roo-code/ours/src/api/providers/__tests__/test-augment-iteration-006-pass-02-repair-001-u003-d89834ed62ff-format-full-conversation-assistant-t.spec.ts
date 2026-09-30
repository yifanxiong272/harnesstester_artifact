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





  __testAugmentVitest_457083e09373.it("format_full_conversation_assistant_tool_use_maps_to_function_call_round_006_pass_02", async () => {
  	// Force fetch fallback to capture request body
  	mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

  	const mockFetch = __testAugmentVitest_457083e09373.vi.fn().mockResolvedValue({
  		ok: true,
  		body: new ReadableStream({ start(controller) { controller.enqueue(new TextEncoder().encode('data: [DONE]\n\n')); controller.close() } }),
  	})
  	global.fetch = mockFetch as any

  	// Assistant message containing a tool_use block
  	const toolUse = { type: "tool_use", id: "toolcall-xyz", name: "assistant-tool", input: { k: 1 } }
  	const messages = [{ role: "assistant", content: [toolUse] }]

  	const stream = handler.createMessage("System prompt", messages)
  	for await (const _ of stream) {
  		// drain
  	}

  	__testAugmentVitest_457083e09373.expect(mockFetch).toHaveBeenCalled()
  	const parsed = JSON.parse(mockFetch.mock.calls[0][1].body as string)
  	// There should be function_call items pushed after assistant message
  	const hasFuncCall = parsed.input.some((it: any) => it.type === "function_call" && (it.call_id || it.call_id === undefined ? true : false))
  	__testAugmentVitest_457083e09373.expect(hasFuncCall).toBe(true)

  	// Locate function_call and verify arguments were JSON-stringified when present
  	const func = parsed.input.find((it: any) => it.type === "function_call")
  	__testAugmentVitest_457083e09373.expect(typeof func.arguments === "string").toBe(true)
  	__testAugmentVitest_457083e09373.expect(func.name).toBe("assistant-tool")
  })
})

// Additional tests for GPT-5 streaming event coverage

import * as __testAugmentVitest_457083e09373 from "vitest";

const __testAugmentLoadTarget_9acec0937018 = async () => {
  __testAugmentVitest_457083e09373.vi.doUnmock("../openai-native.js");
  __testAugmentVitest_457083e09373.vi.resetModules();
  return import("../openai-native.js");
};
