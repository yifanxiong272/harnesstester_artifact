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








	  __testAugmentVitest_4b7ffd4e9f54.it("emits_top_level_reasoning_when_no_reasoning_details_round_011", async () => {
	  	const handler = new OpenRouterHandler({ openRouterApiKey: "test-key", openRouterModelId: "anthropic/claude-sonnet-4" })

	  	const mockStream = {
	  		async *[Symbol.asyncIterator]() {
	  			yield { choices: [{ delta: { reasoning: "top-level thought" } }] }
	  			yield { choices: [{ delta: {} }], usage: { prompt_tokens: 2, completion_tokens: 3, cost: 0 } }
	  		},
	  	}

	  	const mockCreate = __testAugmentVitest_4b7ffd4e9f54.vi.fn().mockResolvedValue(mockStream)
	  	;(OpenAI as any).prototype.chat = { completions: { create: mockCreate } } as any

	  	const generator = handler.createMessage("sys", [])
	  	const seen: any[] = []

	  	for await (const chunk of generator) {
	  		seen.push(chunk)
	  	}

	  	// Should have emitted a single top-level reasoning chunk (and usage)
	  	const reasoning = seen.find((c) => c.type === "reasoning")
	  	__testAugmentVitest_4b7ffd4e9f54.expect(reasoning).toBeDefined()
	  	__testAugmentVitest_4b7ffd4e9f54.expect(reasoning.text).toBe("top-level thought")

	  	// Since there were no reasoning_details fragments, getReasoningDetails should be undefined
	  	__testAugmentVitest_4b7ffd4e9f54.expect(handler.getReasoningDetails()).toBeUndefined()
	  })
	})

})

import * as __testAugmentVitest_4b7ffd4e9f54 from "vitest";

const __testAugmentLoadTarget_d14e02b6a83f = async () => {
  __testAugmentVitest_4b7ffd4e9f54.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_4b7ffd4e9f54.vi.resetModules();
  return import("../openrouter.js");
};
