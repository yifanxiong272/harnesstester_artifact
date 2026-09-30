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




	  __testAugmentVitest_c58330e5a175.it("ensureClient constructor throws_round_016_pass_02", async () => {
	  	// Replace the 'ollama' module so the Ollama constructor throws when instantiated
	  	__testAugmentVitest_c58330e5a175.vi.doMock("ollama", () => ({
	  		Ollama: __testAugmentVitest_c58330e5a175.vi.fn().mockImplementation(() => {
	  			throw new Error("ctor fail")
	  		}),
	  		Message: __testAugmentVitest_c58330e5a175.vi.fn(),
	  	}))

	  	// Mock getOllamaModels so fetchModel doesn't fail before ensureClient is hit
	  	__testAugmentVitest_c58330e5a175.vi.doMock("../fetchers/ollama", () => ({
	  		getOllamaModels: __testAugmentVitest_c58330e5a175.vi.fn().mockResolvedValue({
	  			llama2: { contextWindow: 1024, maxTokens: 1024, supportsImages: false, supportsPromptCache: false },
	  		}),
	  	}))

	  	// Load a fresh copy of the target so our module-level mocks are applied
	  	const { NativeOllamaHandler } = await __testAugmentLoadTarget_4b5e7b4a99dd()

	  	const options = {
	  		apiModelId: "llama2",
	  		ollamaModelId: "llama2",
	  		ollamaBaseUrl: "http://localhost:11434",
	  	}

	  	const localHandler = new NativeOllamaHandler(options)

	  	const stream = localHandler.createMessage("Sys", [{ role: "user", content: "x" }])

	  	// Iteration should surface the constructor error wrapped by ensureClient
	  	await __testAugmentVitest_c58330e5a175.expect(async () => {
	  		for await (const _ of stream) {
	  			// consume
	  		}
	  	}).rejects.toThrow("Error creating Ollama client: ctor fail")
	  })
	})
})

import * as __testAugmentVitest_c58330e5a175 from "vitest";

const __testAugmentLoadTarget_4b5e7b4a99dd = async () => {
  __testAugmentVitest_c58330e5a175.vi.doUnmock("../native-ollama.js");
  __testAugmentVitest_c58330e5a175.vi.resetModules();
  return import("../native-ollama.js");
};
