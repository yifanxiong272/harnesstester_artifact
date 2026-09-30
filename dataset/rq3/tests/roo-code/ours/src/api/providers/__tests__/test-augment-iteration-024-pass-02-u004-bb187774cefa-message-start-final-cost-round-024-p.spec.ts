// npx vitest run src/api/providers/__tests__/minimax.spec.ts

vitest.mock("vscode", () => ({
	workspace: {
		getConfiguration: vitest.fn().mockReturnValue({
			get: vitest.fn().mockReturnValue(600), // Default timeout in seconds
		}),
	},
}))

import { Anthropic } from "@anthropic-ai/sdk"

import { type MinimaxModelId, minimaxDefaultModelId, minimaxModels } from "@roo-code/types"

import { MiniMaxHandler } from "../minimax"

vitest.mock("@anthropic-ai/sdk", () => {
	const mockCreate = vitest.fn()
	return {
		Anthropic: vitest.fn(() => ({
			messages: {
				create: mockCreate,
			},
		})),
	}
})

describe("MiniMaxHandler", () => {
	let handler: MiniMaxHandler
	let mockCreate: any

	beforeEach(() => {
		vitest.clearAllMocks()
		const anthropicInstance = (Anthropic as unknown as any)()
		mockCreate = anthropicInstance.messages.create
	})




	describe("API Methods", () => {
		beforeEach(() => {
			handler = new MiniMaxHandler({ minimaxApiKey: "test-minimax-api-key" })
		})








	  __testAugmentVitest_21826c850e3b.it("message_start_final_cost_round_024_pass_02", async () => {
	  	// Simulate a stream that yields a message_start with input/output and cache tokens, then ends
	  	mockCreate.mockResolvedValueOnce({
	  		[Symbol.asyncIterator]: () => ({
	  			next: __testAugmentVitest_21826c850e3b.vi
	  				.fn()
	  				.mockResolvedValueOnce({
	  					done: false,
	  					value: {
	  						type: "message_start",
	  						message: {
	  							usage: {
	  								input_tokens: 7,
	  								output_tokens: 13,
	  								cache_creation_input_tokens: 2,
	  								cache_read_input_tokens: 1,
	  							},
	  						},
	  					},
	  				})
	  				.mockResolvedValueOnce({ done: true }),
	  			}),
	  	})

	  	const gen = handler.createMessage("system prompt", [])
	  	// First yield: usage from message_start
	  	const first = await gen.next()
	  	__testAugmentVitest_21826c850e3b.expect(first.done).toBe(false)
	  	__testAugmentVitest_21826c850e3b.expect(first.value).toEqual({ type: "usage", inputTokens: 7, outputTokens: 13, cacheWriteTokens: 2, cacheReadTokens: 1 })

	  	// Second yield: final aggregated cost (totalCost should be present and numeric)
	  	const second = await gen.next()
	  	__testAugmentVitest_21826c850e3b.expect(second.done).toBe(false)
	  	__testAugmentVitest_21826c850e3b.expect(second.value.type).toBe("usage")
	  	__testAugmentVitest_21826c850e3b.expect(typeof second.value.totalCost).toBe("number")
	  })
	})

})

import * as __testAugmentVitest_21826c850e3b from "vitest";

const __testAugmentLoadTarget_af05f35b7e70 = async () => {
  __testAugmentVitest_21826c850e3b.vi.doUnmock("../minimax.js");
  __testAugmentVitest_21826c850e3b.vi.resetModules();
  return import("../minimax.js");
};
