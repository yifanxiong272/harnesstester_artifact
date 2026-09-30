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












  __testAugmentVitest_1827a61325f9.it("toolResultToText_unknown_block_type_round_031_pass_02", () => {
  	// Unknown content block types should be serialized using their type in brackets
  	const block: any = {
  		type: "tool_result",
  		tool_use_id: "t-unknown",
  		content: [
  			{ type: "sticker", sticker_meta: { id: "s1" } },
  		],
  	}

  	const result = toolResultToText(block)
  	__testAugmentVitest_1827a61325f9.expect(result).toBe("[Tool Result]\n[sticker]")
  })
})






import * as __testAugmentVitest_1827a61325f9 from "vitest";

const __testAugmentLoadTarget_65a60f2268ca = async () => {
  __testAugmentVitest_1827a61325f9.vi.doUnmock("../index.js");
  __testAugmentVitest_1827a61325f9.vi.resetModules();
  return import("../index.js");
};
