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




	  __testAugmentVitest_c58330e5a175.it("completePrompt error instance wrapped_round_016_pass_03", async () => {
	  	// Ensure models are present
	  	mockGetOllamaModels.mockResolvedValue({
	  		llama2: { contextWindow: 4096, maxTokens: 4096, supportsImages: false, supportsPromptCache: false },
	  	})

	  	// Cause chat to reject with an Error instance
	  	mockChat.mockRejectedValue(new Error("boom"))

	  	await __testAugmentVitest_c58330e5a175.expect(handler.completePrompt("x")).rejects.toThrow("Ollama completion error: boom")
	  })
	})
})

import * as __testAugmentVitest_c58330e5a175 from "vitest";

const __testAugmentLoadTarget_4b5e7b4a99dd = async () => {
  __testAugmentVitest_c58330e5a175.vi.doUnmock("../native-ollama.js");
  __testAugmentVitest_c58330e5a175.vi.resetModules();
  return import("../native-ollama.js");
};
