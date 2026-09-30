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












  __testAugmentVitest_1827a61325f9.it("cleanupAfterTruncation_preserve_condenseParent_when_truncation_orphaned_round_031_pass_02", () => {
  	// Setup: one valid summary exists (so condenseId is present in existingSummaryIds)
  	const validCondense = "valid-cond"
  	const orphanedTrunc = "orphan-trunc"

  	const messages = [
  		{ role: "user", content: "A", condenseParent: validCondense },
  		{ role: "assistant", content: "B", truncationParent: orphanedTrunc },
  		{ role: "user", content: "Summary text", isSummary: true, condenseId: validCondense },
  	]

  	// The assistant message has an orphaned truncationParent but a valid condenseParent scenario needs to be set
  	// Alter message 1 to have both parents so that needsUpdate becomes true due to orphaned truncationParent
  	messages[0].truncationParent = orphanedTrunc

  	const cleaned = cleanupAfterTruncation(messages as any)

  	// Since summary exists, existingSummaryIds includes validCondense; orphaned truncationParent should be cleared
  	// But condenseParent should be preserved because its summary still exists
  	const m0 = cleaned.find((m) => m.content === "A") as any
  	__testAugmentVitest_1827a61325f9.expect(m0).toBeDefined()
  	__testAugmentVitest_1827a61325f9.expect(m0.condenseParent).toBe(validCondense)
  	// truncationParent was orphaned -> should be undefined
  	__testAugmentVitest_1827a61325f9.expect(m0.truncationParent).toBeUndefined()
  })
})






import * as __testAugmentVitest_1827a61325f9 from "vitest";

const __testAugmentLoadTarget_65a60f2268ca = async () => {
  __testAugmentVitest_1827a61325f9.vi.doUnmock("../index.js");
  __testAugmentVitest_1827a61325f9.vi.resetModules();
  return import("../index.js");
};
