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








	  __testAugmentVitest_21826c850e3b.it("add_cache_control_array_round_024_pass_02", async () => {
	  	// Client returns an immediately-completed iterator
	  	mockCreate.mockResolvedValueOnce({
	  		[Symbol.asyncIterator]: () => ({
	  			async next() {
	  				return { done: true }
	  			},
	  		}),
	  	})

	  	// Provide messages where the relevant user messages already have content arrays
	  	const messages = [
	  		{ role: "user", content: [{ type: "text", text: "a" }, { type: "text", text: "b" }] },
	  		{ role: "user", content: [{ type: "text", text: "c" }, { type: "text", text: "d" }] },
	  		{ role: "assistant", content: "ignored" },
	  		{ role: "user", content: [{ type: "text", text: "last1" }, { type: "text", text: "last2" }] },
	  	]

	  	const gen = handler.createMessage("system prompt", messages as any)
	  	await gen.next()

	  	const calledArgs = mockCreate.mock.calls[0][0]
	  	const passedMessages = calledArgs.messages

	  	// Identify user message indices - addCacheControl should only add cache_control to the last element of the last two user messages
	  	// Find the last two user messages in our original array: indices 1 and 3 in this constructed list
	  	// Check that for those messages the last content element has cache_control, and earlier elements do not
	  	const secondLast = passedMessages[1]
	  	const last = passedMessages[3]

	  	__testAugmentVitest_21826c850e3b.expect(secondLast.content[0].cache_control).toBeUndefined()
	  	__testAugmentVitest_21826c850e3b.expect(secondLast.content[1].cache_control).toBeDefined()

	  	__testAugmentVitest_21826c850e3b.expect(last.content[0].cache_control).toBeUndefined()
	  	__testAugmentVitest_21826c850e3b.expect(last.content[last.content.length - 1].cache_control).toBeDefined()
	  })
	})

})

import * as __testAugmentVitest_21826c850e3b from "vitest";

const __testAugmentLoadTarget_af05f35b7e70 = async () => {
  __testAugmentVitest_21826c850e3b.vi.doUnmock("../minimax.js");
  __testAugmentVitest_21826c850e3b.vi.resetModules();
  return import("../minimax.js");
};
