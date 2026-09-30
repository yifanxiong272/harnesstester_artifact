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








	  __testAugmentVitest_21826c850e3b.it("convert_tool_choice_object_function_round_024", async () => {
	  	// Stub the client to finish immediately
	  	mockCreate.mockResolvedValueOnce({
	  		[Symbol.asyncIterator]: () => ({
	  			async next() {
	  				return { done: true }
	  			},
	  		}),
	  	})

	  	// Provide object form { function: { name } } to exercise object branch
	  	const metadata = { tool_choice: { function: { name: "my_tool_fn" } } } as any
	  	const gen = handler.createMessage("system prompt", [], metadata)
	  	await gen.next()

	  	// Expect the Anthropic call to receive a tool_choice object with type: "tool" and the function name
	  	__testAugmentVitest_21826c850e3b.expect(mockCreate).toHaveBeenCalledWith(
	  		__testAugmentVitest_21826c850e3b.expect.objectContaining({
	  			tool_choice: { type: "tool", name: "my_tool_fn" },
	  		}),
	  	)
	  })
	})

})

import * as __testAugmentVitest_21826c850e3b from "vitest";

const __testAugmentLoadTarget_af05f35b7e70 = async () => {
  __testAugmentVitest_21826c850e3b.vi.doUnmock("../minimax.js");
  __testAugmentVitest_21826c850e3b.vi.resetModules();
  return import("../minimax.js");
};
