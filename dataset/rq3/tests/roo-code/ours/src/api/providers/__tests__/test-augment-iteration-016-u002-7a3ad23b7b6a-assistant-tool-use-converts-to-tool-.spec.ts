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




	  __testAugmentVitest_c58330e5a175.it("assistant tool_use converts to tool_calls_round_016", async () => {
	  	// Ensure models are present
	  	mockGetOllamaModels.mockResolvedValue({
	  		llama2: { contextWindow: 4096, maxTokens: 4096, supportsImages: false, supportsPromptCache: false },
	  	})

	  	// Mock chat to be a minimal async generator
	  	mockChat.mockImplementation(async function* () {
	  		yield { message: { content: "assistant reply" } }
	  	})

	  	// Create an assistant message that contains a tool_use block
	  	const messages = [
	  		{
	  			role: "assistant",
	  			content: [
	  				{ type: "text", text: "pre-tool text" },
	  				{ type: "tool_use", name: "get_time", input: { timezone: "UTC" } },
	  			],
	  		},
	  	]

	  	const stream = handler.createMessage("Sys", messages)
	  	// consume
	  	for await (const _ of stream) {
	  		// no-op
	  	}

	  	// The converted Ollama messages should include an assistant message with tool_calls mapping the tool_use
	  	expect(mockChat).toHaveBeenCalledWith(
	  		expect.objectContaining({
	  			messages: expect.arrayContaining([
	  				expect.objectContaining({
	  					role: "assistant",
	  					tool_calls: expect.arrayContaining([
	  						expect.objectContaining({
	  							function: expect.objectContaining({ name: "get_time", arguments: expect.objectContaining({ timezone: "UTC" }) }),
	  						}),
	  					]),
	  				}),
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
