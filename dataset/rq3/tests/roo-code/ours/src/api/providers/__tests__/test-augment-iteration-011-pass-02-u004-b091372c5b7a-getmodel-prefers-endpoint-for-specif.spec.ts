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








	  __testAugmentVitest_4b7ffd4e9f54.it("getModel_prefers_endpoint_for_specific_provider_round_011_pass_02", async () => {
	  	// Create handler with a specific provider requested
	  	const opts = { openRouterApiKey: "k", openRouterModelId: "openai/some-model", openRouterSpecificProvider: "custom-prov" }
	  	const handler = new OpenRouterHandler(opts)

	  	// Populate models and endpoints caches directly to avoid async fetchers
	  	handler.models = {
	  		"openai/some-model": { maxTokens: 50, description: "model entry" },
	  	}

	  	handler.endpoints = {
	  		"custom-prov": { maxTokens: 12345, description: "provider endpoint", supportsPromptCache: false },
	  	}

	  	// Act: call getModel which should prefer the endpoint entry for the specific provider
	  	const result = handler.getModel()

	  	// Assert that the returned info comes from the endpoints map
	  	__testAugmentVitest_4b7ffd4e9f54.expect(result).toBeDefined()
	  	__testAugmentVitest_4b7ffd4e9f54.expect(result.info).toBeDefined()
	  	__testAugmentVitest_4b7ffd4e9f54.expect(result.info.maxTokens).toBe(12345)
	  	__testAugmentVitest_4b7ffd4e9f54.expect(result.info.description).toBe("provider endpoint")
	  })
	})

})

import * as __testAugmentVitest_4b7ffd4e9f54 from "vitest";

const __testAugmentLoadTarget_d14e02b6a83f = async () => {
  __testAugmentVitest_4b7ffd4e9f54.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_4b7ffd4e9f54.vi.resetModules();
  return import("../openrouter.js");
};
