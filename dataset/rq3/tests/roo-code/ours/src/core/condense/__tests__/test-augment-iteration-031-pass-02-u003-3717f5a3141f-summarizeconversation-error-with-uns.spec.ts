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












  __testAugmentVitest_1827a61325f9.it("summarizeConversation_error_with_unserializable_response_round_031_pass_02", async () => {
  	// Create an Error with status, code and circular response/body to trigger serialization fallback
  	const err: any = new Error("boom")
  	err.status = 500
  	err.code = "E500"
  	const circular: any = {}
  	circular.self = circular
  	err.response = circular
  	err.body = circular

  	mockApiHandler.createMessage = __testAugmentVitest_1827a61325f9.vi.fn(() => {
  		throw err
  	}) as any

  	const messages = [
  		{ role: "user", content: "1", ts: 1 },
  		{ role: "assistant", content: "2", ts: 2 },
  		{ role: "user", content: "3", ts: 3 },
  		{ role: "assistant", content: "4", ts: 4 },
  		{ role: "user", content: "5", ts: 5 },
  		{ role: "assistant", content: "6", ts: 6 },
  		{ role: "user", content: "7", ts: 7 },
  	]

  	const result = await summarizeConversation({
  		messages,
  		apiHandler: mockApiHandler,
  		systemPrompt: defaultSystemPrompt,
  		taskId,
  	})

  	// Should return an error and include the structured pieces and fallback serialization messages
  	__testAugmentVitest_1827a61325f9.expect(result.error).toBeTruthy()
  	__testAugmentVitest_1827a61325f9.expect(result.errorDetails).toContain("Error: boom")
  	__testAugmentVitest_1827a61325f9.expect(result.errorDetails).toContain("HTTP Status: 500")
  	__testAugmentVitest_1827a61325f9.expect(result.errorDetails).toContain("Error Code: E500")
  	// Because response/body are circular, the implementation should append the Unable to serialize markers
  	__testAugmentVitest_1827a61325f9.expect(result.errorDetails).toContain("Unable to serialize")
  })
})






import * as __testAugmentVitest_1827a61325f9 from "vitest";

const __testAugmentLoadTarget_65a60f2268ca = async () => {
  __testAugmentVitest_1827a61325f9.vi.doUnmock("../index.js");
  __testAugmentVitest_1827a61325f9.vi.resetModules();
  return import("../index.js");
};
