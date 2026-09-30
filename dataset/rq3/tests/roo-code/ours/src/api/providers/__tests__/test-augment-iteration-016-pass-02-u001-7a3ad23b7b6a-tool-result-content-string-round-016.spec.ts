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




	  __testAugmentVitest_c58330e5a175.it("tool_result content string_round_016_pass_02", async () => {
	  	// Ensure models are present
	  	mockGetOllamaModels.mockResolvedValue({
	  		llama2: { contextWindow: 4096, maxTokens: 4096, supportsImages: true, supportsPromptCache: false },
	  	})

	  	// Mock chat to be a minimal async generator
	  	mockChat.mockImplementation(async function* () {
	  		yield { message: { content: "ok" } }
	  	})

	  	// user message with a tool_result whose content is a plain string
	  	const messages = [
	  		{
	  			role: "user",
	  			content: [
	  				{
	  					type: "tool_result",
	  					content: "simple tool result string",
	  				},
	  			],
	  		},
	  	]

	  	const stream = handler.createMessage("Sys", messages)
	  	for await (const _ of stream) {
	  		// consume
	  	}

	  	// Verify the tool_result string was propagated into an Ollama user message content
	  	expect(mockChat).toHaveBeenCalledWith(
	  		expect.objectContaining({
	  			messages: expect.arrayContaining([
	  				expect.objectContaining({ role: "user", content: "simple tool result string" }),
	  			]),
	  		}),
	  	)
	  })
	})
})

import * as __testAugmentVitest_c58330e5a175 from "vitest";

const __testAugmentLoadTarget_4b5e7b4a99dd = async () => {
  __testAugmentVitest_c58330e5a175.vi.doUnmock("../native-ollama.js");
  __testAugmentVitest_c58330e5a175.vi.resetModules();
  return import("../native-ollama.js");
};
