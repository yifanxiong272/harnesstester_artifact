// pnpm --filter roo-cline test api/providers/__tests__/openrouter.spec.ts

vitest.mock("vscode", () => ({}))

import { Anthropic } from "@anthropic-ai/sdk"
import OpenAI from "openai"

import { OpenRouterHandler } from "../openrouter"
import { ApiHandlerOptions } from "../../../shared/api"
import { Package } from "../../../shared/package"

vitest.mock("openai")
vitest.mock("delay", () => ({ default: vitest.fn(() => Promise.resolve()) }))

vitest.mock("../fetchers/modelCache", () => ({
	getModels: vitest.fn().mockImplementation(() => {
		return Promise.resolve({
			"anthropic/claude-sonnet-4": {
				maxTokens: 8192,
				contextWindow: 200000,
				supportsImages: true,
				supportsPromptCache: true,
				inputPrice: 3,
				outputPrice: 15,
				cacheWritesPrice: 3.75,
				cacheReadsPrice: 0.3,
				description: "Claude 3.7 Sonnet",
				thinking: false,
			},
			"anthropic/claude-sonnet-4.5": {
				maxTokens: 8192,
				contextWindow: 200000,
				supportsImages: true,
				supportsPromptCache: true,
				inputPrice: 3,
				outputPrice: 15,
				cacheWritesPrice: 3.75,
				cacheReadsPrice: 0.3,
				description: "Claude 4.5 Sonnet",
				thinking: false,
			},
			"anthropic/claude-3.7-sonnet:thinking": {
				maxTokens: 128000,
				contextWindow: 200000,
				supportsImages: true,
				supportsPromptCache: true,
				inputPrice: 3,
				outputPrice: 15,
				cacheWritesPrice: 3.75,
				cacheReadsPrice: 0.3,
				description: "Claude 3.7 Sonnet with thinking",
			},
			"openai/gpt-4o": {
				maxTokens: 16384,
				contextWindow: 128000,
				supportsImages: true,
				supportsPromptCache: false,
				inputPrice: 2.5,
				outputPrice: 10,
				description: "GPT-4o",
			},
			"openai/o1": {
				maxTokens: 100000,
				contextWindow: 200000,
				supportsImages: true,
				supportsPromptCache: false,
				inputPrice: 15,
				outputPrice: 60,
				description: "OpenAI o1",
				excludedTools: ["existing_excluded"],
				includedTools: ["existing_included"],
			},
		})
	}),
}))

describe("OpenRouterHandler", () => {
	const mockOptions: ApiHandlerOptions = {
		openRouterApiKey: "test-key",
		openRouterModelId: "anthropic/claude-sonnet-4",
	}

	beforeEach(() => vitest.clearAllMocks())



	describe("createMessage", () => {








	  __testAugmentVitest_4b7ffd4e9f54.it("injects_fake_encrypted_block_for_gemini_tool_calls_round_011_pass_03", async () => {
	  	// Arrange: capture the params passed to the OpenAI client's create()
	  	let capturedCreateArg: any = null
	  	const mockCreate = __testAugmentVitest_4b7ffd4e9f54.vi.fn().mockImplementation(async (params: any) => {
	  		capturedCreateArg = params
	  		// Return an async iterable that immediately completes
	  		return {
	  			async *[Symbol.asyncIterator]() {
	  				return
	  			},
	  		}
	  	})

	  	// Mock the openai client so the provider uses our mockCreate
	  	__testAugmentVitest_4b7ffd4e9f54.vi.doMock("openai", () => {
	  		return {
	  			default: __testAugmentVitest_4b7ffd4e9f54.vi.fn().mockImplementation(() => ({ chat: { completions: { create: mockCreate } } })),
	  		}
	  	})

	  	// Mock convertToOpenAiMessages to return a message array with an assistant message that has tool_calls
	  	__testAugmentVitest_4b7ffd4e9f54.vi.doMock("../../transform/openai-format", () => ({
	  		convertToOpenAiMessages: (messages: any) => {
	  			return [
	  				{ role: "system", content: "system" },
	  				{
	  					role: "assistant",
	  					// Simulate tool_calls present and no reasoning_details
	  					tool_calls: [{ id: "tool-first", index: 0, function: { name: "do_it" }, function_call: null }],
	  				},
	  			]
	  		},
	  		sanitizeGeminiMessages: (msgs: any) => msgs,
	  		convertToR1Format: (m: any) => m,
	  	}))

	  	// Minimal fetcher mocks so module loads predictably
	  	__testAugmentVitest_4b7ffd4e9f54.vi.doMock("../fetchers/modelCache", () => ({ getModels: __testAugmentVitest_4b7ffd4e9f54.vi.fn().mockResolvedValue({ "google/gemini-2.5-pro": { maxTokens: 100 } }) }))
	  	__testAugmentVitest_4b7ffd4e9f54.vi.doMock("../fetchers/modelEndpointCache", () => ({ getModelEndpoints: __testAugmentVitest_4b7ffd4e9f54.vi.fn().mockResolvedValue({}) }))

	  	// Load a fresh copy of the target module with the above mocks applied
	  	const mod = await __testAugmentLoadTarget_d14e02b6a83f()
	  	const { OpenRouterHandler } = mod

	  	// Act: instantiate handler for a Gemini model and call createMessage to trigger injection logic
	  	const handler = new OpenRouterHandler({ openRouterApiKey: "k", openRouterModelId: "google/gemini-2.5-pro" })
	  	// Trigger the createMessage path and wait for the underlying create() to be called
	  	await handler.createMessage("sys-prompt", []).next().catch(() => null)

	  	// Assert: the create() call received a messages array in which assistant message has reasoning_details injected
	  	__testAugmentVitest_4b7ffd4e9f54.expect(capturedCreateArg).not.toBeNull()
	  	const messages = capturedCreateArg?.messages
	  	__testAugmentVitest_4b7ffd4e9f54.expect(Array.isArray(messages)).toBe(true)
	  	const assistantMsg = messages.find((m: any) => m.role === "assistant")
	  	__testAugmentVitest_4b7ffd4e9f54.expect(assistantMsg).toBeDefined()
	  	__testAugmentVitest_4b7ffd4e9f54.expect(Array.isArray((assistantMsg as any).reasoning_details)).toBe(true)
	  	const fakeEncrypted = (assistantMsg as any).reasoning_details.find((d: any) => d.type === "reasoning.encrypted")
	  	__testAugmentVitest_4b7ffd4e9f54.expect(fakeEncrypted).toBeDefined()
	  	__testAugmentVitest_4b7ffd4e9f54.expect(fakeEncrypted.data).toBe("skip_thought_signature_validator")
	  	__testAugmentVitest_4b7ffd4e9f54.expect(fakeEncrypted.format).toBe("google-gemini-v1")
	  	__testAugmentVitest_4b7ffd4e9f54.expect(fakeEncrypted.index).toBe(0)
	  	__testAugmentVitest_4b7ffd4e9f54.expect(fakeEncrypted.id).toBe("tool-first")
	  })
	})

})

import * as __testAugmentVitest_4b7ffd4e9f54 from "vitest";

const __testAugmentLoadTarget_d14e02b6a83f = async () => {
  __testAugmentVitest_4b7ffd4e9f54.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_4b7ffd4e9f54.vi.resetModules();
  return import("../openrouter.js");
};
