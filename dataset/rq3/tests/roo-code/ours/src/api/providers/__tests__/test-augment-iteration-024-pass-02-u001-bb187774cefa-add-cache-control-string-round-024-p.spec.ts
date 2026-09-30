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








	  __testAugmentVitest_21826c850e3b.it("add_cache_control_string_round_024_pass_02", async () => {
	  	// Ensure client returns an immediately-completed iterator so createMessage proceeds to call
	  	mockCreate.mockResolvedValueOnce({
	  		[Symbol.asyncIterator]: () => ({
	  			async next() {
	  				return { done: true }
	  			},
	  		}),
	  	})

	  	// Build messages where the last two user messages are string content and should get cache_control
	  	const messages = [
	  		{ role: "user", content: "first user message" },
	  		{ role: "assistant", content: "assistant reply" },
	  		{ role: "user", content: "second user message" },
	  		{ role: "user", content: "third user message" },
	  	]

	  	const gen = handler.createMessage("system prompt", messages as any)
	  	// advance generator to trigger mockCreate invocation
	  	await gen.next()

	  	// Inspect the request that was passed to the Anthropic client
	  	const calledArgs = mockCreate.mock.calls[0][0]
	  	const passedMessages = calledArgs.messages

	  	// The last two user messages (indices 2 and 3) should have been converted to content arrays with cache_control
	  	__testAugmentVitest_21826c850e3b.expect(passedMessages[2].role).toBe("user")
	  	__testAugmentVitest_21826c850e3b.expect(Array.isArray(passedMessages[2].content)).toBe(true)
	  	__testAugmentVitest_21826c850e3b.expect(passedMessages[2].content[0].cache_control).toBeDefined()

	  	__testAugmentVitest_21826c850e3b.expect(passedMessages[3].role).toBe("user")
	  	__testAugmentVitest_21826c850e3b.expect(Array.isArray(passedMessages[3].content)).toBe(true)
	  	__testAugmentVitest_21826c850e3b.expect(passedMessages[3].content[0].cache_control).toBeDefined()
	  })
	})

})

import * as __testAugmentVitest_21826c850e3b from "vitest";

const __testAugmentLoadTarget_af05f35b7e70 = async () => {
  __testAugmentVitest_21826c850e3b.vi.doUnmock("../minimax.js");
  __testAugmentVitest_21826c850e3b.vi.resetModules();
  return import("../minimax.js");
};
