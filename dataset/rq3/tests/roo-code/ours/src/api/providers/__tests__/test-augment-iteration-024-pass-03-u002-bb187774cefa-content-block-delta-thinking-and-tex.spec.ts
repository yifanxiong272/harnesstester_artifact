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








	  __testAugmentVitest_21826c850e3b.it("content_block_delta_thinking_and_text_delta_round_024_pass_03", async () => {
	  	// Stream containing content_block_delta with thinking_delta and text_delta
	  	mockCreate.mockResolvedValueOnce({
	  		[Symbol.asyncIterator]: () => ({
	  			next: __testAugmentVitest_21826c850e3b.vi
	  				.fn()
	  				.mockResolvedValueOnce({
	  					done: false,
	  					value: { type: "content_block_delta", delta: { type: "thinking_delta", thinking: "partial thought" } },
	  				})
	  				.mockResolvedValueOnce({
	  					done: false,
	  					value: { type: "content_block_delta", delta: { type: "text_delta", text: "partial text" } },
	  				})
	  				.mockResolvedValueOnce({ done: true }),
	  		}),
	  	})

	  	const gen = handler.createMessage("sys", [])

	  	const first = await gen.next()
	  	__testAugmentVitest_21826c850e3b.expect(first.done).toBe(false)
	  	__testAugmentVitest_21826c850e3b.expect(first.value).toEqual({ type: "reasoning", text: "partial thought" })

	  	const second = await gen.next()
	  	__testAugmentVitest_21826c850e3b.expect(second.done).toBe(false)
	  	__testAugmentVitest_21826c850e3b.expect(second.value).toEqual({ type: "text", text: "partial text" })
	  })
	})

})

import * as __testAugmentVitest_21826c850e3b from "vitest";

const __testAugmentLoadTarget_af05f35b7e70 = async () => {
  __testAugmentVitest_21826c850e3b.vi.doUnmock("../minimax.js");
  __testAugmentVitest_21826c850e3b.vi.resetModules();
  return import("../minimax.js");
};
