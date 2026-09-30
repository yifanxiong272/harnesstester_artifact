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












  __testAugmentVitest_1827a61325f9.it("summarizeConversation_multiple_usage_chunks_override_cost_round_031_pass_02", async () => {
  	// Stream that yields multiple usage chunks; the final usage chunk should determine cost
  	const multiUsageStream = (async function* () {
  		yield { type: "text" as const, text: "first" }
  		yield { type: "usage" as const, totalCost: 0.01, outputTokens: 10 }
  		yield { type: "text" as const, text: "second" }
  		yield { type: "usage" as const, totalCost: 0.09, outputTokens: 90 }
  	})()

  	mockApiHandler.createMessage = __testAugmentVitest_1827a61325f9.vi.fn().mockReturnValue(multiUsageStream) as any
  	mockApiHandler.countTokens = __testAugmentVitest_1827a61325f9.vi.fn().mockResolvedValue(20) as any

  	const messages = [
  		{ role: "user", content: "x", ts: 1 },
  		{ role: "assistant", content: "y", ts: 2 },
  		{ role: "user", content: "z", ts: 3 },
  		{ role: "assistant", content: "w", ts: 4 },
  		{ role: "user", content: "u", ts: 5 },
  		{ role: "assistant", content: "v", ts: 6 },
  		{ role: "user", content: "t", ts: 7 },
  	]

  	const result = await summarizeConversation({
  		messages,
  		apiHandler: mockApiHandler,
  		systemPrompt: defaultSystemPrompt,
  		taskId,
  	})

  	// The summary should be the concatenation of text chunks (trimmed)
  	__testAugmentVitest_1827a61325f9.expect(result.summary).toBe("firstsecond")
  	// The final usage totalCost (0.09) should be recorded
  	__testAugmentVitest_1827a61325f9.expect(result.cost).toBe(0.09)
  	// newContextTokens should reflect the mocked countTokens result
  	__testAugmentVitest_1827a61325f9.expect(result.newContextTokens).toBe(20)
  })
})






import * as __testAugmentVitest_1827a61325f9 from "vitest";

const __testAugmentLoadTarget_65a60f2268ca = async () => {
  __testAugmentVitest_1827a61325f9.vi.doUnmock("../index.js");
  __testAugmentVitest_1827a61325f9.vi.resetModules();
  return import("../index.js");
};
