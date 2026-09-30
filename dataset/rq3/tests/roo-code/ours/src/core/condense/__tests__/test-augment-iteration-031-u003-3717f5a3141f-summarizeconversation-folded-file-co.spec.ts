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












  __testAugmentVitest_1827a61325f9.it("summarizeConversation_folded_file_context_included_round_031", async () => {
  	// Mock folded file context to return sections and load the target after registering the mock
  	const mockGenerate = __testAugmentVitest_1827a61325f9.vi.fn(async () => ({
  		sections: [
  			"<system-reminder>\n// Folded file: src/foo.ts\nfunction foo() {}\n</system-reminder>",
  		],
  	}))

  	// Register mock for foldedFileContext used by summarizeConversation before loading target
  	__testAugmentVitest_1827a61325f9.vi.doMock("../foldedFileContext", () => ({
  		generateFoldedFileContext: mockGenerate,
  	}))

  	// Load a fresh copy of the target so our mock is used
  	const {
  		summarizeConversation: loadedSummarize,
  	} = await __testAugmentLoadTarget_65a60f2268ca()

  	// Use the suite's mockApiHandler; ensure it produces a summary
  	const messages = [
  		{ role: "user", content: "start", ts: 1 },
  		{ role: "assistant", content: "ack", ts: 2 },
  		{ role: "user", content: "please summarize", ts: 3 },
  		{ role: "assistant", content: "ok", ts: 4 },
  		{ role: "user", content: "final", ts: 5 },
  	]

  	const result = await loadedSummarize({
  		messages,
  		apiHandler: mockApiHandler,
  		systemPrompt: defaultSystemPrompt,
  		taskId,
  		filesReadByRoo: ["src/foo.ts"],
  		cwd: "/repo",
  	})

  	// The mocked generateFoldedFileContext should have been called
  	__testAugmentVitest_1827a61325f9.expect(mockGenerate).toHaveBeenCalledWith(["src/foo.ts"], {
  		cwd: "/repo",
  		rooIgnoreController: undefined,
  	})

  	// Summary message should include the folded section as its own content block
  	const summaryMessage = result.messages.find((m) => m.isSummary)
  	__testAugmentVitest_1827a61325f9.expect(summaryMessage).toBeDefined()
  	const contentBlocks = summaryMessage!.content as any[]
  	// Should have at least one content block containing the folded file reminder text
  	const hasFolded = contentBlocks.some((b) => typeof b.text === "string" && b.text.includes("Folded file: src/foo.ts"))
  	__testAugmentVitest_1827a61325f9.expect(hasFolded).toBe(true)
  })
})






import * as __testAugmentVitest_1827a61325f9 from "vitest";

const __testAugmentLoadTarget_65a60f2268ca = async () => {
  __testAugmentVitest_1827a61325f9.vi.doUnmock("../index.js");
  __testAugmentVitest_1827a61325f9.vi.resetModules();
  return import("../index.js");
};
