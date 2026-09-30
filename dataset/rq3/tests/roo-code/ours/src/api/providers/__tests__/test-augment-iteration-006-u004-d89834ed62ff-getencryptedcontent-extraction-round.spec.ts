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





  __testAugmentVitest_457083e09373.it("getEncryptedContent returns reasoning encrypted content_round_006", () => {
  	// Prime the handler's lastResponseOutput with a reasoning item
  	;(handler as any).lastResponseOutput = [
  		{ type: "text", text: "ignore" },
  		{ type: "reasoning", encrypted_content: "ENCRYPTED-VALUE", id: "reasoning-123" },
  	]

  	const enc = handler.getEncryptedContent()
  	__testAugmentVitest_457083e09373.expect(enc).toBeDefined()
  	__testAugmentVitest_457083e09373.expect(enc!.encrypted_content).toBe("ENCRYPTED-VALUE")
  	__testAugmentVitest_457083e09373.expect(enc!.id).toBe("reasoning-123")

  	// And verify undefined when no output exists
  	;(handler as any).lastResponseOutput = undefined
  	__testAugmentVitest_457083e09373.expect(handler.getEncryptedContent()).toBeUndefined()
  })
})

// Additional tests for GPT-5 streaming event coverage

import * as __testAugmentVitest_457083e09373 from "vitest";

const __testAugmentLoadTarget_9acec0937018 = async () => {
  __testAugmentVitest_457083e09373.vi.doUnmock("../openai-native.js");
  __testAugmentVitest_457083e09373.vi.resetModules();
  return import("../openai-native.js");
};
