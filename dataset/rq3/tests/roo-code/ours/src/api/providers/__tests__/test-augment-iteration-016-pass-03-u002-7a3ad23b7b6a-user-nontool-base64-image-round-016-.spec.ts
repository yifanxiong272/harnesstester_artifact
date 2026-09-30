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




	  __testAugmentVitest_c58330e5a175.it("user-nonTool-base64-image_round_016_pass_03", async () => {
	  	// Ensure models are present
	  	mockGetOllamaModels.mockResolvedValue({
	  		llama2: { contextWindow: 4096, maxTokens: 4096, supportsImages: true, supportsPromptCache: false },
	  	})

	  	// Minimal chat response
	  	mockChat.mockImplementation(async function* () {
	  		yield { message: { content: "ok" } }
	  	})

	  	// User message with text and a base64 image in the non-tool content path
	  	const messages = [
	  		{
	  			role: "user",
	  			content: [
	  				{ type: "text", text: "Hello" },
	  				{ type: "image", source: { type: "base64", data: "BASE64_DATA" } },
	  			],
	  		},
	  	]

	  	const stream = handler.createMessage("System prompt", messages)
	  	for await (const _ of stream) {
	  		// consume
	  	}

	  	// Verify the Ollama client call included a user message with images containing the base64 data
	  	const calledArgs = mockChat.mock.calls[mockChat.mock.calls.length - 1][0]
	  	__testAugmentVitest_c58330e5a175.expect(calledArgs.messages).toEqual(__testAugmentVitest_c58330e5a175.expect.arrayContaining([
	  		expect.objectContaining({ role: "system", content: "System prompt" }),
	  		expect.objectContaining({ role: "user", content: "Hello", images: ["BASE64_DATA"] }),
	  	]))
	  })
	})
})

import * as __testAugmentVitest_c58330e5a175 from "vitest";

const __testAugmentLoadTarget_4b5e7b4a99dd = async () => {
  __testAugmentVitest_c58330e5a175.vi.doUnmock("../native-ollama.js");
  __testAugmentVitest_c58330e5a175.vi.resetModules();
  return import("../native-ollama.js");
};
