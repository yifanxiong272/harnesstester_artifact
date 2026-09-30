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








	  __testAugmentVitest_21826c850e3b.it("content_block_delta_input_json_delta_yields_tool_call_partial_round_024", async () => {
	  	const partialJson = { arg: 123 }

	  	// Return a streaming response that yields a content_block_delta / input_json_delta chunk
	  	mockCreate.mockResolvedValueOnce({
	  		[Symbol.asyncIterator]: () => ({
	  			next: __testAugmentVitest_21826c850e3b.vi
	  				.fn()
	  				.mockResolvedValueOnce({
	  					done: false,
	  					value: {
	  						type: "content_block_delta",
	  						index: 0,
	  						delta: { type: "input_json_delta", partial_json: partialJson },
	  					},
	  				})
	  				.mockResolvedValueOnce({ done: true }),
	  			}),
	  	})

	  	const gen = handler.createMessage("system prompt", [])
	  	const first = await gen.next()

	  	__testAugmentVitest_21826c850e3b.expect(first.done).toBe(false)
	  	__testAugmentVitest_21826c850e3b.expect(first.value).toEqual({
	  		type: "tool_call_partial",
	  		index: 0,
	  		id: undefined,
	  		name: undefined,
	  		arguments: partialJson,
	  	})
	  })
	})

})

import * as __testAugmentVitest_21826c850e3b from "vitest";

const __testAugmentLoadTarget_af05f35b7e70 = async () => {
  __testAugmentVitest_21826c850e3b.vi.doUnmock("../minimax.js");
  __testAugmentVitest_21826c850e3b.vi.resetModules();
  return import("../minimax.js");
};
