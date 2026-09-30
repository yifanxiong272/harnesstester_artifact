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





  __testAugmentVitest_457083e09373.it("output_item_done_emits_tool_call_when_no_partials_round_006_pass_02", async () => {
  	const model = handler.getModel()

  	// Ensure no previously streamed partial tool-call ids
  	;(handler as any).streamedToolCallIds.clear()
  	// Ensure we haven't observed text output in the current response
  	;(handler as any).sawTextOutputInCurrentResponse = false

  	const item = {
  		type: "function_call",
  		call_id: "call-42",
  		name: "fnName",
  		arguments: { foo: "bar" },
  	}

  	const event = { type: "response.output_item.done", item }

  	const out: any[] = []
  	for await (const chunk of (handler as any).processEvent(event, model)) {
  		out.push(chunk)
  	}

  	__testAugmentVitest_457083e09373.expect(out.length).toBeGreaterThan(0)
  	// Expect a single tool_call yielded for the complete function_call (no partials existed)
  	const match = out.find((c) => c.type === "tool_call")
  	__testAugmentVitest_457083e09373.expect(match).toBeDefined()
  	__testAugmentVitest_457083e09373.expect(match.id).toBe("call-42")
  	__testAugmentVitest_457083e09373.expect(match.name).toBe("fnName")
  	// arguments are normalized to a JSON string for object inputs
  	__testAugmentVitest_457083e09373.expect(match.arguments).toBe(JSON.stringify(item.arguments))
  })
})

// Additional tests for GPT-5 streaming event coverage

import * as __testAugmentVitest_457083e09373 from "vitest";

const __testAugmentLoadTarget_9acec0937018 = async () => {
  __testAugmentVitest_457083e09373.vi.doUnmock("../openai-native.js");
  __testAugmentVitest_457083e09373.vi.resetModules();
  return import("../openai-native.js");
};
