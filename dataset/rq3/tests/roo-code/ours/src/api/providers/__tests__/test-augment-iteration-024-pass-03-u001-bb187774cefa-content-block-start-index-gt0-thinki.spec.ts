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








	  __testAugmentVitest_21826c850e3b.it("content_block_start_index_gt0_thinking_and_text_round_024_pass_03", async () => {
	  	// Stream with two content_block_start chunks with index > 0 to force newline yields before content
	  	mockCreate.mockResolvedValueOnce({
	  		[Symbol.asyncIterator]: () => ({
	  			next: __testAugmentVitest_21826c850e3b.vi
	  				.fn()
	  				.mockResolvedValueOnce({
	  					done: false,
	  					value: {
	  						type: "content_block_start",
	  						index: 1,
	  						content_block: { type: "thinking", thinking: "inner thought" },
	  					},
	  				})
	  				.mockResolvedValueOnce({
	  					done: false,
	  					value: {
	  						type: "content_block_start",
	  						index: 1,
	  						content_block: { type: "text", text: "follow-up text" },
	  					},
	  				})
	  				.mockResolvedValueOnce({ done: true }),
	  		}),
	  	})

	  	const gen = handler.createMessage("sys", [])

	  	const a = await gen.next()
	  	__testAugmentVitest_21826c850e3b.expect(a.done).toBe(false)
	  	__testAugmentVitest_21826c850e3b.expect(a.value).toEqual({ type: "reasoning", text: "\n" })

	  	const b = await gen.next()
	  	__testAugmentVitest_21826c850e3b.expect(b.done).toBe(false)
	  	__testAugmentVitest_21826c850e3b.expect(b.value).toEqual({ type: "reasoning", text: "inner thought" })

	  	const c = await gen.next()
	  	__testAugmentVitest_21826c850e3b.expect(c.done).toBe(false)
	  	__testAugmentVitest_21826c850e3b.expect(c.value).toEqual({ type: "text", text: "\n" })

	  	const d = await gen.next()
	  	__testAugmentVitest_21826c850e3b.expect(d.done).toBe(false)
	  	__testAugmentVitest_21826c850e3b.expect(d.value).toEqual({ type: "text", text: "follow-up text" })
	  })
	})

})

import * as __testAugmentVitest_21826c850e3b from "vitest";

const __testAugmentLoadTarget_af05f35b7e70 = async () => {
  __testAugmentVitest_21826c850e3b.vi.doUnmock("../minimax.js");
  __testAugmentVitest_21826c850e3b.vi.resetModules();
  return import("../minimax.js");
};
