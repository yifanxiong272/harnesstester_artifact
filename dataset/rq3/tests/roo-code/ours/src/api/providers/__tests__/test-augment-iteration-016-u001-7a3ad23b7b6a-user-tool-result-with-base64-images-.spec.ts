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




	  __testAugmentVitest_c58330e5a175.it("user tool_result with base64 images_round_016", async () => {
	  	// Ensure models are present
	  	mockGetOllamaModels.mockResolvedValue({
	  		llama2: { contextWindow: 4096, maxTokens: 4096, supportsImages: true, supportsPromptCache: false },
	  	})

	  	// Mock chat to be a minimal async generator so createMessage runs and calls the client
	  	mockChat.mockImplementation(async function* () {
	  		yield { message: { content: "ok" } }
	  	})

	  	// Craft an Anthropic user message where content is structured and contains a tool_result
	  	const messages = [
	  		{
	  			role: "user",
	  			content: [
	  				{
	  					type: "tool_result",
	  					content: [
	  						{ type: "image", source: { type: "base64", data: "BASE64_IMAGE_DATA" } },
	  						{ type: "text", text: "Insight from tool" },
	  					],
	  				},
	  			],
	  		},
	  	]

	  	const stream = handler.createMessage("System prompt", messages)
	  	// consume the stream
	  	for await (const _ of stream) {
	  		// no-op
	  	}

	  	// The converted Ollama messages should include a user message created from the tool_result
	  	expect(mockChat).toHaveBeenCalledWith(
	  		expect.objectContaining({
	  			messages: expect.arrayContaining([
	  				expect.objectContaining({
	  					role: "user",
	  					images: ["BASE64_IMAGE_DATA"],
	  					content: expect.stringContaining("(see following user message for image)"),
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
