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












  __testAugmentVitest_1827a61325f9.it("summarizeConversation_preserve_existing_condenseParent_round_031_pass_02", async () => {
  	// Ensure we have a deterministic summary response
  	const stream = (async function* () {
  		yield { type: "text" as const, text: "preserve test summary" }
  		yield { type: "usage" as const, totalCost: 0.02, outputTokens: 10 }
  	})()
  	// Override the suite's mockApiHandler createMessage for this test
  	mockApiHandler.createMessage = __testAugmentVitest_1827a61325f9.vi.fn().mockReturnValue(stream) as any
  	mockApiHandler.countTokens = __testAugmentVitest_1827a61325f9.vi.fn().mockResolvedValue(5) as any

  	// One message already has a condenseParent and should be left unchanged
  	const preExisting = "pre-existing-condense"
  	const messages = [
  		{ role: "user", content: "first", ts: 1, condenseParent: preExisting },
  		{ role: "assistant", content: "second", ts: 2 },
  		{ role: "user", content: "third", ts: 3 },
  		{ role: "assistant", content: "fourth", ts: 4 },
  		{ role: "user", content: "fifth", ts: 5 },
  		{ role: "assistant", content: "sixth", ts: 6 },
  		{ role: "user", content: "seventh", ts: 7 },
  	]

  	const result = await summarizeConversation({
  		messages,
  		apiHandler: mockApiHandler,
  		systemPrompt: defaultSystemPrompt,
  		taskId,
  	})

  	const summaryMessage = result.messages.find((m) => m.isSummary)
  	__testAugmentVitest_1827a61325f9.expect(summaryMessage).toBeDefined()
  	const newCondenseId = summaryMessage!.condenseId
  	__testAugmentVitest_1827a61325f9.expect(newCondenseId).toBeDefined()

  	// The message that already had condenseParent should keep its original value
  	const kept = result.messages.find((m) => m.ts === 1)
  	__testAugmentVitest_1827a61325f9.expect(kept).toBeDefined()
  	__testAugmentVitest_1827a61325f9.expect(kept!.condenseParent).toBe(preExisting)

  	// Other original messages (without condenseParent) should have been tagged with the new condenseId
  	for (const m of result.messages.filter((m) => !m.isSummary && m.ts !== 1)) {
  		__testAugmentVitest_1827a61325f9.expect(m.condenseParent).toBe(newCondenseId)
  	}
  })
})






import * as __testAugmentVitest_1827a61325f9 from "vitest";

const __testAugmentLoadTarget_65a60f2268ca = async () => {
  __testAugmentVitest_1827a61325f9.vi.doUnmock("../index.js");
  __testAugmentVitest_1827a61325f9.vi.resetModules();
  return import("../index.js");
};
