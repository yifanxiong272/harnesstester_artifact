// npx vitest run api/providers/__tests__/native-ollama.spec.ts

import { NativeOllamaHandler } from "../native-ollama"
import { ApiHandlerOptions } from "../../../shared/api"
import { getOllamaModels } from "../fetchers/ollama"

// Mock the ollama package
const mockChat = vitest.fn()
vitest.mock("ollama", () => {
	return {
		Ollama: vitest.fn().mockImplementation(() => ({
			chat: mockChat,
		})),
		Message: vitest.fn(),
	}
})

// Mock the getOllamaModels function
vitest.mock("../fetchers/ollama", () => ({
	getOllamaModels: vitest.fn(),
}))

const mockGetOllamaModels = vitest.mocked(getOllamaModels)

describe("NativeOllamaHandler", () => {
	let handler: NativeOllamaHandler

	beforeEach(() => {
		vitest.clearAllMocks()

		// Default mock for getOllamaModels
		mockGetOllamaModels.mockResolvedValue({
			llama2: {
				contextWindow: 4096,
				maxTokens: 4096,
				supportsImages: false,
				supportsPromptCache: false,
			},
		})

		const options: ApiHandlerOptions = {
			apiModelId: "llama2",
			ollamaModelId: "llama2",
			ollamaBaseUrl: "http://localhost:11434",
		}

		handler = new NativeOllamaHandler(options)
	})





	describe("tool calling", () => {




	  __testAugmentVitest_c58330e5a175.it("assistant-only-image-parts_round_016_pass_03", async () => {
	  	// Ensure models are present
	  	mockGetOllamaModels.mockResolvedValue({
	  		llama2: { contextWindow: 4096, maxTokens: 4096, supportsImages: false, supportsPromptCache: false },
	  	})

	  	// Minimal chat response so createMessage proceeds
	  	mockChat.mockImplementation(async function* () {
	  		yield { message: { content: "ok" } }
	  	})

	  	// Assistant message containing only an image block (assistant shouldn't send images -> maps to empty strings)
	  	const messages = [
	  		{
	  			role: "assistant",
	  			content: [
	  				{ type: "image", source: { type: "base64", data: "IMG" } },
	  			],
	  		},
	  	]

	  	const stream = handler.createMessage("Sys", messages)
	  	for await (const _ of stream) {
	  		// consume stream
	  	}

	  	// Inspect the last call to the mocked Ollama client
	  	const lastCall = mockChat.mock.calls[mockChat.mock.calls.length - 1][0]
	  	const assistantMsg = lastCall.messages.find((m: any) => m.role === "assistant")

	  	// The assistant content should be an empty string (image parts map to "")
	  	__testAugmentVitest_c58330e5a175.expect(assistantMsg.content).toBe("")

	  	// Ensure raw image data isn't embedded in the content
	  	__testAugmentVitest_c58330e5a175.expect(assistantMsg.content).not.toContain("IMG")

	  	// No tool_use blocks were present, so tool_calls should be undefined
	  	__testAugmentVitest_c58330e5a175.expect(assistantMsg.tool_calls).toBeUndefined()
	  })
	})
})

import * as __testAugmentVitest_c58330e5a175 from "vitest";

const __testAugmentLoadTarget_4b5e7b4a99dd = async () => {
  __testAugmentVitest_c58330e5a175.vi.doUnmock("../native-ollama.js");
  __testAugmentVitest_c58330e5a175.vi.resetModules();
  return import("../native-ollama.js");
};
