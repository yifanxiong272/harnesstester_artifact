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








	  __testAugmentVitest_4b7ffd4e9f54.it("yields_and_accumulates_reasoning_details_across_chunks_round_011", async () => {
	  	const handler = new OpenRouterHandler({ openRouterApiKey: "test-key", openRouterModelId: "anthropic/claude-sonnet-4" })

	  	// Stream emits two partial reasoning_details fragments for the same index/type,
	  	// then emits usage so the generator completes and consolidation runs.
	  	const mockStream = {
	  		async *[Symbol.asyncIterator]() {
	  			// First fragment
	  			yield {
	  				choices: [
	  					{
	  						delta: {
	  							reasoning_details: [
	  								{ type: "reasoning.text", text: "part1", index: 0 },
	  							],
	  						},
	  					},
	  				],
	  			}

	  			// Second fragment (should append to the accumulator)
	  			yield {
	  				choices: [
	  					{
	  						delta: {
	  							reasoning_details: [
	  								{ type: "reasoning.text", text: "part2", index: 0 },
	  							],
	  						},
	  					},
	  				],
	  			}

	  			// Final chunk with usage to trigger final yielded usage and completion
	  			yield {
	  				choices: [{ delta: {} }],
	  				usage: { prompt_tokens: 1, completion_tokens: 2, cost: 0.0 },
	  			}
	  		},
	  	}

	  	const mockCreate = __testAugmentVitest_4b7ffd4e9f54.vi.fn().mockResolvedValue(mockStream)
	  	;(OpenAI as any).prototype.chat = { completions: { create: mockCreate } } as any

	  	const generator = handler.createMessage("sys", [])
	  	const chunks: any[] = []

	  	for await (const chunk of generator) {
	  		chunks.push(chunk)
	  	}

	  	// Expect two reasoning partial yields (part1 and part2)
	  	const reasoningChunks = chunks.filter((c) => c.type === "reasoning").map((c) => c.text)
	  	__testAugmentVitest_4b7ffd4e9f54.expect(reasoningChunks).toEqual(["part1", "part2"])

	  	// After completion, consolidated reasoning details should be available and contain concatenated text
	  	const consolidated = handler.getReasoningDetails()
	  	__testAugmentVitest_4b7ffd4e9f54.expect(consolidated).toBeDefined()
	  	__testAugmentVitest_4b7ffd4e9f54.expect(consolidated && consolidated.length).toBeGreaterThan(0)
	  	// The accumulation logic joins fragments; ensure the stored text contains both parts
	  	__testAugmentVitest_4b7ffd4e9f54.expect(consolidated && String(consolidated[0].text)).toContain("part1")
	  	__testAugmentVitest_4b7ffd4e9f54.expect(consolidated && String(consolidated[0].text)).toContain("part2")
	  })
	})

})

import * as __testAugmentVitest_4b7ffd4e9f54 from "vitest";

const __testAugmentLoadTarget_d14e02b6a83f = async () => {
  __testAugmentVitest_4b7ffd4e9f54.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_4b7ffd4e9f54.vi.resetModules();
  return import("../openrouter.js");
};
