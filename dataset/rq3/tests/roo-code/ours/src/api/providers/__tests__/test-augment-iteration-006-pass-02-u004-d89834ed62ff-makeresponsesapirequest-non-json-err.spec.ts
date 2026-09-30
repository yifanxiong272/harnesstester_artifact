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





  __testAugmentVitest_457083e09373.it("makeResponsesApiRequest_non_json_error_body_includes_raw_text_round_006_pass_02", async () => {
  	const model = handler.getModel()

  	// Mock fetch to return an HTTP error with a non-JSON body
  	const mockFetch = __testAugmentVitest_457083e09373.vi.fn().mockResolvedValue({
  		ok: false,
  		status: 401,
  		text: async () => "plain-error-body",
  	})
  	global.fetch = mockFetch as any

  	const requestBody = { model: model.id, input: [], stream: true }

  	await __testAugmentVitest_457083e09373.expect(async () => {
  		for await (const _ of (handler as any).makeResponsesApiRequest(requestBody, model)) {
  			// drain
  		}
  	}).rejects.toThrow(/Authentication failed/)

  	// The thrown message should include the raw text from the body
  	await __testAugmentVitest_457083e09373.expect(async () => {
  		for await (const _ of (handler as any).makeResponsesApiRequest(requestBody, model)) {
  			// drain
  		}
  	}).rejects.toThrow(/plain-error-body/)

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
