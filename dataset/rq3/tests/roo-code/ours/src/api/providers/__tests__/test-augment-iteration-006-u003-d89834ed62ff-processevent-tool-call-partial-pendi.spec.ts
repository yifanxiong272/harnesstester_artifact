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





  __testAugmentVitest_457083e09373.it("processEvent emits tool_call_partial using pending identity_round_006", async () => {
  	const model = handler.getModel()

  	// First, simulate an output_item.added that captures the tool identity
  	const addedEvent = {
  		type: "response.output_item.added",
  		item: {
  			type: "function_call",
  			call_id: "cid1",
  			name: "toolName",
  			arguments: '{"pre":true}',
  		},
  	}

  	// Process the identity event (no guarantee of yielded chunks, but this sets pendingToolCallId/name)
  	for await (const _c of (handler as any).processEvent(addedEvent, model)) {
  		// drain any yielded chunks
  	}

  	// Now send a delta-only tool_call_arguments event without explicit id/name
  	const deltaEvent = {
  		type: "response.tool_call_arguments.delta",
  		delta: '{"arg":1}',
  		index: 2,
  	}

  	const out: any[] = []
  	for await (const chunk of (handler as any).processEvent(deltaEvent, model)) {
  		out.push(chunk)
  	}

  	__testAugmentVitest_457083e09373.expect(out.length).toBeGreaterThan(0)
  	__testAugmentVitest_457083e09373.expect(out[0].type).toBe("tool_call_partial")
  	__testAugmentVitest_457083e09373.expect(out[0].id).toBe("cid1")
  	__testAugmentVitest_457083e09373.expect(out[0].name).toBe("toolName")
  	__testAugmentVitest_457083e09373.expect(out[0].arguments).toBe('{"arg":1}')
  })
})

// Additional tests for GPT-5 streaming event coverage

import * as __testAugmentVitest_457083e09373 from "vitest";

const __testAugmentLoadTarget_9acec0937018 = async () => {
  __testAugmentVitest_457083e09373.vi.doUnmock("../openai-native.js");
  __testAugmentVitest_457083e09373.vi.resetModules();
  return import("../openai-native.js");
};
