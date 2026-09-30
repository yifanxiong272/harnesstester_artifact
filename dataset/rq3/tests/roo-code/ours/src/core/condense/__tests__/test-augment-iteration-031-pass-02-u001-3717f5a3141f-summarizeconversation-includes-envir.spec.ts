// npx vitest core/condense/__tests__/index.spec.ts

import type { Mock } from "vitest"

import { Anthropic } from "@anthropic-ai/sdk"

import { ApiHandler } from "../../../api"
import { ApiMessage } from "../../task-persistence/apiMessages"
import { maybeRemoveImageBlocks } from "../../../api/transform/image-cleaning"
import {
	summarizeConversation,
	getMessagesSinceLastSummary,
	getEffectiveApiHistory,
	cleanupAfterTruncation,
	extractCommandBlocks,
	injectSyntheticToolResults,
	toolUseToText,
	toolResultToText,
	convertToolBlocksToText,
	transformMessagesForCondensing,
} from "../index"

vi.mock("../../../api/transform/image-cleaning", () => ({
	maybeRemoveImageBlocks: vi.fn((messages: ApiMessage[], _apiHandler: ApiHandler) => [...messages]),
}))

const taskId = "test-task-id"






describe("summarizeConversation", () => {
	// Mock ApiHandler
	let mockApiHandler: ApiHandler
	let mockStream: AsyncGenerator<any, void, unknown>

	beforeEach(() => {
		// Reset mocks
		vi.clearAllMocks()

		// Setup mock stream with usage information
		mockStream = (async function* () {
			yield { type: "text" as const, text: "This is " }
			yield { type: "text" as const, text: "a summary" }
			yield { type: "usage" as const, totalCost: 0.05, outputTokens: 150 }
		})()

		// Setup mock API handler
		mockApiHandler = {
			createMessage: vi.fn().mockReturnValue(mockStream),
			countTokens: vi.fn().mockImplementation(() => Promise.resolve(100)),
			getModel: vi.fn().mockReturnValue({
				id: "test-model",
				info: {
					contextWindow: 8000,
					supportsImages: true,
					supportsVision: true,
					maxTokens: 4000,
					supportsPromptCache: true,
					maxCachePoints: 10,
					minTokensPerCachePoint: 100,
					cachableFields: ["system", "messages"],
				},
			}),
		} as unknown as ApiHandler
	})

	// Default system prompt for tests
	const defaultSystemPrompt = "You are a helpful assistant."












  __testAugmentVitest_1827a61325f9.it("summarizeConversation_includes_environment_and_tool_tokens_round_031_pass_02", async () => {
  	// Prepare messages (>=2 since getMessagesSinceLastSummary must allow summarization)
  	const messages = [
  		{ role: "user", content: "m1", ts: 1 },
  		{ role: "assistant", content: "m2", ts: 2 },
  		{ role: "user", content: "m3", ts: 3 },
  		{ role: "assistant", content: "m4", ts: 4 },
  		{ role: "user", content: "m5", ts: 5 },
  		{ role: "assistant", content: "m6", ts: 6 },
  		{ role: "user", content: "m7", ts: 7 },
  	]

  	// Create a stream that yields a summary and usage
  	const envStream = (async function* () {
  		yield { type: "text" as const, text: "Environment aware summary" }
  		yield { type: "usage" as const, totalCost: 0.04, outputTokens: 80 }
  	})()

  	// Override the apiHandler createMessage and countTokens for this test
  	mockApiHandler.createMessage = __testAugmentVitest_1827a61325f9.vi.fn().mockReturnValue(envStream) as any
  	mockApiHandler.countTokens = __testAugmentVitest_1827a61325f9.vi.fn().mockResolvedValue(100) as any

  	const environmentDetails = "ENV: PATH=/usr/local/bin"

  	const result = await summarizeConversation({
  		messages,
  		apiHandler: mockApiHandler,
  		systemPrompt: defaultSystemPrompt,
  		taskId,
  		isAutomaticTrigger: true,
  		environmentDetails,
  		metadata: { tools: [{ name: "tool-a", description: "desc" }] } as any,
  	})

  	// API must have been invoked
  	__testAugmentVitest_1827a61325f9.expect(mockApiHandler.createMessage).toHaveBeenCalled()

  	// Summary message must exist and include the environmentDetails block as a text content block
  	const summaryMessage = result.messages.find((m) => m.isSummary)
  	__testAugmentVitest_1827a61325f9.expect(summaryMessage).toBeDefined()
  	const content = summaryMessage!.content as any[]
  	__testAugmentVitest_1827a61325f9.expect(content.some((b) => typeof b.text === "string" && b.text.includes("ENV: PATH=/usr/local/bin"))).toBe(true)

  	// countTokens should be called for both the system+summary and the serialized tools
  	__testAugmentVitest_1827a61325f9.expect(mockApiHandler.countTokens).toHaveBeenCalled()
  	__testAugmentVitest_1827a61325f9.expect(mockApiHandler.countTokens).toHaveBeenCalledTimes(2)

  	// Given countTokens returns 100 each time in this test, newContextTokens should be 200
  	__testAugmentVitest_1827a61325f9.expect(result.newContextTokens).toBe(200)
  	__testAugmentVitest_1827a61325f9.expect(result.cost).toBe(0.04)
  })
})






import * as __testAugmentVitest_1827a61325f9 from "vitest";

const __testAugmentLoadTarget_65a60f2268ca = async () => {
  __testAugmentVitest_1827a61325f9.vi.doUnmock("../index.js");
  __testAugmentVitest_1827a61325f9.vi.resetModules();
  return import("../index.js");
};
