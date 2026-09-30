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








	  __testAugmentVitest_4b7ffd4e9f54.it("uses_convertToR1Format_for_deepseek_models_round_011_pass_03", async () => {
	  	// Sentinel array to be returned by convertToR1Format
	  	const sentinel = [{ role: "user", content: "r1-system" }, { role: "user", content: "r1-user" }]

	  	// Mock convertToR1Format
	  	__testAugmentVitest_4b7ffd4e9f54.vi.doMock("../../transform/r1-format", () => ({ convertToR1Format: (__: any) => sentinel }))

	  	// Mock convertToOpenAiMessages harmlessly (not expected to be used)
	  	__testAugmentVitest_4b7ffd4e9f54.vi.doMock("../../transform/openai-format", () => ({
	  		convertToOpenAiMessages: () => [{ role: "system", content: "should-not-be-used" }],
	  		sanitizeGeminiMessages: (m: any) => m,
	  		convertToR1Format: (m: any) => sentinel,
	  	}))

	  	// Minimal fetcher mocks
	  	__testAugmentVitest_4b7ffd4e9f54.vi.doMock("../fetchers/modelCache", () => ({ getModels: __testAugmentVitest_4b7ffd4e9f54.vi.fn().mockResolvedValue({ "deepseek/deepseek-r1-x": { maxTokens: 200 } }) }))
	  	__testAugmentVitest_4b7ffd4e9f54.vi.doMock("../fetchers/modelEndpointCache", () => ({ getModelEndpoints: __testAugmentVitest_4b7ffd4e9f54.vi.fn().mockResolvedValue({}) }))

	  	// Capture the messages passed to create()
	  	let capturedMessages: any = null
	  	const mockCreate = __testAugmentVitest_4b7ffd4e9f54.vi.fn().mockImplementation(async (params: any) => {
	  		capturedMessages = params.messages
	  		return { async *[Symbol.asyncIterator]() { return } }
	  	})
	  	__testAugmentVitest_4b7ffd4e9f54.vi.doMock("openai", () => ({ default: __testAugmentVitest_4b7ffd4e9f54.vi.fn().mockImplementation(() => ({ chat: { completions: { create: mockCreate } } })) }))

	  	// Load target and run
	  	const mod = await __testAugmentLoadTarget_d14e02b6a83f()
	  	const { OpenRouterHandler } = mod
	  	const handler = new OpenRouterHandler({ openRouterApiKey: "k", openRouterModelId: "deepseek/deepseek-r1-x" })
	  	await handler.createMessage("sys", []).next().catch(() => null)

	  	// Assert: the messages passed to create() are exactly the sentinel from convertToR1Format
	  	__testAugmentVitest_4b7ffd4e9f54.expect(capturedMessages).toEqual(sentinel)
	  })
	})

})

import * as __testAugmentVitest_4b7ffd4e9f54 from "vitest";

const __testAugmentLoadTarget_d14e02b6a83f = async () => {
  __testAugmentVitest_4b7ffd4e9f54.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_4b7ffd4e9f54.vi.resetModules();
  return import("../openrouter.js");
};
