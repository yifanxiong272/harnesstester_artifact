// npx vitest run api/providers/__tests__/openai-native.spec.ts

import { Anthropic } from "@anthropic-ai/sdk"
import OpenAI from "openai"

import {} from "@roo-code/types"

import { OpenAiNativeHandler } from "../openai-native"
import { ApiHandlerOptions } from "../../../shared/api"

// Mock OpenAI client - now everything uses Responses API
const mockResponsesCreate = vitest.fn()

vitest.mock("openai", () => {
	return {
		__esModule: true,
		default: vitest.fn().mockImplementation(() => ({
			responses: {
				create: mockResponsesCreate,
			},
		})),
	}
})

describe("OpenAiNativeHandler", () => {
	let handler: OpenAiNativeHandler
	let mockOptions: ApiHandlerOptions
	const systemPrompt = "You are a helpful assistant."
	const messages: Anthropic.Messages.MessageParam[] = [
		{
			role: "user",
			content: "Hello!",
		},
	]

	beforeEach(() => {
		mockOptions = {
			apiModelId: "gpt-4.1",
			openAiNativeApiKey: "test-api-key",
		}
		handler = new OpenAiNativeHandler(mockOptions)
		mockResponsesCreate.mockClear()
		// Clear fetch mock if it exists
		if ((global as any).fetch) {
			delete (global as any).fetch
		}
	})

	afterEach(() => {
		// Clean up fetch mock
		if ((global as any).fetch) {
			delete (global as any).fetch
		}
	})

	describe("constructor", () => {
		it("should initialize with provided options", () => {
			expect(handler).toBeInstanceOf(OpenAiNativeHandler)
			expect(handler.getModel().id).toBe(mockOptions.apiModelId)
		})

		it("should initialize with empty API key", () => {
			const handlerWithoutKey = new OpenAiNativeHandler({
				apiModelId: "gpt-4.1",
				openAiNativeApiKey: "",
			})
			expect(handlerWithoutKey).toBeInstanceOf(OpenAiNativeHandler)
		})

		it("should pass undefined baseURL when openAiNativeBaseUrl is empty string", () => {
			;(OpenAI as unknown as ReturnType<typeof vitest.fn>).mockClear()
			new OpenAiNativeHandler({
				apiModelId: "gpt-4.1",
				openAiNativeApiKey: "test-key",
				openAiNativeBaseUrl: "",
			})
			expect(OpenAI).toHaveBeenCalledWith(expect.objectContaining({ baseURL: undefined }))
		})

		it("should pass custom baseURL when openAiNativeBaseUrl is a valid URL", () => {
			;(OpenAI as unknown as ReturnType<typeof vitest.fn>).mockClear()
			new OpenAiNativeHandler({
				apiModelId: "gpt-4.1",
				openAiNativeApiKey: "test-key",
				openAiNativeBaseUrl: "https://custom-openai.example.com/v1",
			})
			expect(OpenAI).toHaveBeenCalledWith(
				expect.objectContaining({ baseURL: "https://custom-openai.example.com/v1" }),
			)
		})
	})

	describe("createMessage", () => {
		it("should handle streaming responses via Responses API", async () => {
			// Mock fetch for Responses API fallback
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode('data: {"type":"response.text.delta","delta":"Test"}\n\n'),
						)
						controller.enqueue(
							new TextEncoder().encode('data: {"type":"response.text.delta","delta":" response"}\n\n'),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.done","response":{"usage":{"prompt_tokens":10,"completion_tokens":2}}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail so it falls back to fetch
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			expect(chunks.length).toBeGreaterThan(0)
			const textChunks = chunks.filter((chunk) => chunk.type === "text")
			expect(textChunks).toHaveLength(2)
			expect(textChunks[0].text).toBe("Test")
			expect(textChunks[1].text).toBe(" response")
		})

		it("should handle API errors", async () => {
			// Mock fetch to return error
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: false,
				status: 500,
				text: async () => "Internal Server Error",
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			const stream = handler.createMessage(systemPrompt, messages)
			await expect(async () => {
				for await (const _chunk of stream) {
					// Should not reach here
				}
			}).rejects.toThrow("OpenAI service error")
		})
	})

	describe("completePrompt", () => {
		it("should handle non-streaming completion using Responses API", async () => {
			// Mock the responses.create method to return a non-streaming response
			mockResponsesCreate.mockResolvedValue({
				output: [
					{
						type: "message",
						content: [
							{
								type: "output_text",
								text: "This is the completion response",
							},
						],
					},
				],
			})

			const result = await handler.completePrompt("Test prompt")

			expect(result).toBe("This is the completion response")
			expect(mockResponsesCreate).toHaveBeenCalledWith(
				expect.objectContaining({
					model: "gpt-4.1",
					stream: false,
					store: false,
					input: [
						{
							role: "user",
							content: [{ type: "input_text", text: "Test prompt" }],
						},
					],
				}),
				expect.objectContaining({
					signal: expect.any(Object),
				}),
			)
		})

		it("should handle SDK errors in completePrompt", async () => {
			// Mock SDK to throw an error
			mockResponsesCreate.mockRejectedValue(new Error("API Error"))

			await expect(handler.completePrompt("Test prompt")).rejects.toThrow(
				"OpenAI Native completion error: API Error",
			)
		})

		it("should return empty string when no text in response", async () => {
			// Mock the responses.create method to return a response without text
			mockResponsesCreate.mockResolvedValue({
				output: [
					{
						type: "message",
						content: [],
					},
				],
			})

			const result = await handler.completePrompt("Test prompt")

			expect(result).toBe("")
		})
	})

	describe("getModel", () => {
		it("should return model info", () => {
			const modelInfo = handler.getModel()
			expect(modelInfo.id).toBe(mockOptions.apiModelId)
			expect(modelInfo.info).toBeDefined()
			expect(modelInfo.info.maxTokens).toBe(32768)
			expect(modelInfo.info.contextWindow).toBe(1047576)
		})

		it("should return GPT-5.3 Codex model info when selected", () => {
			const codexHandler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.3-codex",
			})

			const modelInfo = codexHandler.getModel()
			expect(modelInfo.id).toBe("gpt-5.3-codex")
			expect(modelInfo.info.maxTokens).toBe(128000)
			expect(modelInfo.info.contextWindow).toBe(400000)
			expect(modelInfo.info.supportsReasoningEffort).toEqual(["low", "medium", "high", "xhigh"])
		})

		it("should return GPT-5.4 model info when selected", () => {
			const gpt54Handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.4",
			})

			const modelInfo = gpt54Handler.getModel()
			expect(modelInfo.id).toBe("gpt-5.4")
			expect(modelInfo.info.maxTokens).toBe(128000)
			expect(modelInfo.info.contextWindow).toBe(1_050_000)
			expect(modelInfo.info.supportsVerbosity).toBe(true)
			expect(modelInfo.info.supportsReasoningEffort).toEqual(["none", "low", "medium", "high", "xhigh"])
			expect(modelInfo.info.reasoningEffort).toBe("none")
		})

		it("should return GPT-5.4 Mini model info when selected", () => {
			const gpt54MiniHandler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.4-mini",
			})

			const modelInfo = gpt54MiniHandler.getModel()
			expect(modelInfo.id).toBe("gpt-5.4-mini")
			expect(modelInfo.info.maxTokens).toBe(128000)
			expect(modelInfo.info.contextWindow).toBe(400000)
			expect(modelInfo.info.supportsVerbosity).toBe(true)
			expect(modelInfo.info.supportsReasoningEffort).toEqual(["none", "low", "medium", "high", "xhigh"])
			expect(modelInfo.info.reasoningEffort).toBe("none")
			expect(modelInfo.info.longContextPricing).toBeUndefined()
		})

		it("should return GPT-5.4 Nano model info when selected", () => {
			const gpt54NanoHandler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.4-nano",
			})

			const modelInfo = gpt54NanoHandler.getModel()
			expect(modelInfo.id).toBe("gpt-5.4-nano")
			expect(modelInfo.info.maxTokens).toBe(128000)
			expect(modelInfo.info.contextWindow).toBe(400000)
			expect(modelInfo.info.supportsVerbosity).toBe(true)
			expect(modelInfo.info.supportsReasoningEffort).toEqual(["none", "low", "medium", "high", "xhigh"])
			expect(modelInfo.info.reasoningEffort).toBe("none")
			expect(modelInfo.info.outputPrice).toBe(1.25)
			expect(modelInfo.info.longContextPricing).toBeUndefined()
			expect(modelInfo.info.tiers).toEqual([
				expect.objectContaining({
					name: "flex",
					outputPrice: 0.625,
				}),
			])
		})

		it("should return GPT-5.3 Chat model info when selected", () => {
			const chatHandler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.3-chat-latest",
			})

			const modelInfo = chatHandler.getModel()
			expect(modelInfo.id).toBe("gpt-5.3-chat-latest")
			expect(modelInfo.info.maxTokens).toBe(16_384)
			expect(modelInfo.info.contextWindow).toBe(128000)
			expect(modelInfo.info.supportsImages).toBe(true)
		})

		it("should handle undefined model ID", () => {
			const handlerWithoutModel = new OpenAiNativeHandler({
				openAiNativeApiKey: "test-api-key",
			})
			const modelInfo = handlerWithoutModel.getModel()
			expect(modelInfo.id).toBe("gpt-5.1-codex-max") // Default model
			expect(modelInfo.info).toBeDefined()
		})
	})

	describe("GPT-5 models", () => {
		it("should handle GPT-5 model with Responses API", async () => {
			// Mock fetch for Responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						// Simulate actual GPT-5 Responses API SSE stream format
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.created","response":{"id":"test","status":"in_progress"}}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"Hello"}}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":" world"}}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.done","response":{"usage":{"prompt_tokens":10,"completion_tokens":2}}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail so it uses fetch
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1",
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Verify Responses API is called with correct parameters
			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					method: "POST",
					headers: expect.objectContaining({
						"Content-Type": "application/json",
						Authorization: "Bearer test-api-key",
					}),
					body: expect.any(String),
				}),
			)
			const body1 = (mockFetch.mock.calls[0][1] as any).body as string
			const parsedBody = JSON.parse(body1)
			expect(parsedBody.model).toBe("gpt-5.1")
			expect(parsedBody.instructions).toBe("You are a helpful assistant.")
			// Now using structured format with content arrays (no system prompt in input; it's provided via `instructions`)
			expect(parsedBody.input).toEqual([
				{
					role: "user",
					content: [{ type: "input_text", text: "Hello!" }],
				},
			])
			expect(parsedBody.reasoning?.effort).toBe("medium")
			expect(parsedBody.reasoning?.summary).toBe("auto")
			expect(parsedBody.text?.verbosity).toBe("medium")
			// GPT-5 models don't include temperature
			expect(parsedBody.temperature).toBeUndefined()
			expect(parsedBody.max_output_tokens).toBeDefined()

			// Verify the streamed content
			const textChunks = chunks.filter((c) => c.type === "text")
			expect(textChunks).toHaveLength(2)
			expect(textChunks[0].text).toBe("Hello")
			expect(textChunks[1].text).toBe(" world")
		})

		it("should handle GPT-5.4 model with Responses API", async () => {
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"GPT-5.4 reply"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.4",
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					body: expect.any(String),
				}),
			)
			const body = (mockFetch.mock.calls[0][1] as any).body as string
			const parsedBody = JSON.parse(body)
			expect(parsedBody.model).toBe("gpt-5.4")
			expect(parsedBody.max_output_tokens).toBe(128000)
			expect(parsedBody.temperature).toBeUndefined()
			expect(parsedBody.include).toEqual(["reasoning.encrypted_content"])
			expect(parsedBody.reasoning?.effort).toBe("none")
			expect(parsedBody.text?.verbosity).toBe("medium")

			const textChunks = chunks.filter((chunk) => chunk.type === "text")
			expect(textChunks).toHaveLength(1)
			expect(textChunks[0].text).toBe("GPT-5.4 reply")
		})

		it("should handle GPT-5.3 Chat model with Responses API", async () => {
			// Mock fetch for Responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"Chat reply"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail so it uses fetch
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.3-chat-latest",
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					body: expect.any(String),
				}),
			)
			const body = (mockFetch.mock.calls[0][1] as any).body as string
			const parsedBody = JSON.parse(body)
			expect(parsedBody.model).toBe("gpt-5.3-chat-latest")
			expect(parsedBody.max_output_tokens).toBe(16_384)
			expect(parsedBody.temperature).toBe(0)
			expect(parsedBody.reasoning?.effort).toBeUndefined()
			expect(parsedBody.text?.verbosity).toBeUndefined()

			const textChunks = chunks.filter((chunk) => chunk.type === "text")
			expect(textChunks).toHaveLength(1)
			expect(textChunks[0].text).toBe("Chat reply")
		})

		it("should handle GPT-5-mini model with Responses API", async () => {
			// Mock fetch for Responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"Response"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5-mini-2025-08-07",
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Verify correct model and default parameters
			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					body: expect.stringContaining('"model":"gpt-5-mini-2025-08-07"'),
				}),
			)
		})

		it("should handle GPT-5-nano model with Responses API", async () => {
			// Mock fetch for Responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"Nano response"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5-nano-2025-08-07",
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Verify correct model
			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					body: expect.stringContaining('"model":"gpt-5-nano-2025-08-07"'),
				}),
			)
		})

		it("should support verbosity control for GPT-5", async () => {
			// Mock fetch for Responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"Low verbosity"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1",
				verbosity: "low", // Set verbosity through options
			})

			// Create a message to verify verbosity is passed
			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Verify that verbosity is passed in the request
			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					body: expect.stringContaining('"verbosity":"low"'),
				}),
			)
		})

		it("should support minimal reasoning effort for GPT-5", async () => {
			// Mock fetch for Responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"Minimal effort"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1",
				reasoningEffort: "minimal" as any, // GPT-5 supports minimal
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// With minimal reasoning effort, the model should pass it through
			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					body: expect.stringContaining('"effort":"minimal"'),
				}),
			)
		})

		it("should support xhigh reasoning effort for GPT-5.1 Codex Max", async () => {
			// Mock fetch for Responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"XHigh effort"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1-codex-max",
				reasoningEffort: "xhigh",
			})

			const stream = handler.createMessage(systemPrompt, messages)
			for await (const _chunk of stream) {
				// drain
			}

			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					body: expect.stringContaining('"effort":"xhigh"'),
				}),
			)
		})

		it("should omit reasoning when selection is 'disable'", async () => {
			// Mock fetch for Responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"No reasoning"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			const handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1",
				reasoningEffort: "disable" as any,
			})

			const stream = handler.createMessage(systemPrompt, messages)
			for await (const _ of stream) {
				// drain
			}

			const bodyStr = (mockFetch.mock.calls[0][1] as any).body as string
			const parsed = JSON.parse(bodyStr)
			expect(parsed.reasoning).toBeUndefined()
			expect(parsed.include).toBeUndefined()
		})

		it("should support low reasoning effort for GPT-5", async () => {
			// Mock fetch for Responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"Low effort response"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1",
				reasoningEffort: "low",
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Should use Responses API with low reasoning effort
			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					body: expect.any(String),
				}),
			)
			const body2 = (mockFetch.mock.calls[0][1] as any).body as string
			const parsedBody = JSON.parse(body2)
			expect(parsedBody.model).toBe("gpt-5.1")
			expect(parsedBody.reasoning?.effort).toBe("low")
			expect(parsedBody.reasoning?.summary).toBe("auto")
			expect(parsedBody.text?.verbosity).toBe("medium")
			// GPT-5 models don't include temperature
			expect(parsedBody.temperature).toBeUndefined()
			expect(parsedBody.max_output_tokens).toBeDefined()
		})

		it("should support both verbosity and reasoning effort together for GPT-5", async () => {
			// Mock fetch for Responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"High verbosity minimal effort"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1",
				verbosity: "high",
				reasoningEffort: "minimal" as any,
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Should use Responses API with both parameters
			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					body: expect.any(String),
				}),
			)
			const body3 = (mockFetch.mock.calls[0][1] as any).body as string
			const parsedBody = JSON.parse(body3)
			expect(parsedBody.model).toBe("gpt-5.1")
			expect(parsedBody.reasoning?.effort).toBe("minimal")
			expect(parsedBody.reasoning?.summary).toBe("auto")
			expect(parsedBody.text?.verbosity).toBe("high")
			// GPT-5 models don't include temperature
			expect(parsedBody.temperature).toBeUndefined()
			expect(parsedBody.max_output_tokens).toBeDefined()
		})

		it("should handle actual GPT-5 Responses API format", async () => {
			// Mock fetch with actual response format from GPT-5
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						// Test actual GPT-5 response format
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.created","response":{"id":"test","status":"in_progress"}}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.in_progress","response":{"status":"in_progress"}}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"First text"}}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":" Second text"}}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"reasoning","text":"Some reasoning"}}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.done","response":{"usage":{"prompt_tokens":100,"completion_tokens":20}}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1",
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Should handle the actual format correctly
			const textChunks = chunks.filter((c) => c.type === "text")
			const reasoningChunks = chunks.filter((c) => c.type === "reasoning")

			expect(textChunks).toHaveLength(2)
			expect(textChunks[0].text).toBe("First text")
			expect(textChunks[1].text).toBe(" Second text")

			expect(reasoningChunks).toHaveLength(1)
			expect(reasoningChunks[0].text).toBe("Some reasoning")

			// Should also have usage information with cost
			const usageChunks = chunks.filter((c) => c.type === "usage")
			expect(usageChunks).toHaveLength(1)
			expect(usageChunks[0]).toMatchObject({
				type: "usage",
				inputTokens: 100,
				outputTokens: 20,
				totalCost: expect.any(Number),
			})

			// Verify cost calculation (GPT-5 pricing: input $1.25/M, output $10/M)
			const expectedInputCost = (100 / 1_000_000) * 1.25
			const expectedOutputCost = (20 / 1_000_000) * 10.0
			const expectedTotalCost = expectedInputCost + expectedOutputCost
			expect(usageChunks[0].totalCost).toBeCloseTo(expectedTotalCost, 10)
		})

		it("should handle Responses API with no content gracefully", async () => {
			// Mock fetch with empty response
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(new TextEncoder().encode('data: {"someField":"value"}\n\n'))
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1",
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []

			// Should not throw, just warn
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Should have no content chunks when stream is empty
			const contentChunks = chunks.filter((c) => c.type === "text" || c.type === "reasoning")

			expect(contentChunks).toHaveLength(0)
		})

		it("should handle unhandled stream events gracefully", async () => {
			// Mock fetch for the fallback SSE path
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"Hello"}}\n\n',
							),
						)
						// This event is not handled, so it should be ignored
						controller.enqueue(
							new TextEncoder().encode('data: {"type":"response.audio.delta","delta":"..."}\n\n'),
						)
						controller.enqueue(new TextEncoder().encode('data: {"type":"response.done","response":{}}\n\n'))
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1",
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			const errors: any[] = []

			try {
				for await (const chunk of stream) {
					chunks.push(chunk)
				}
			} catch (error) {
				errors.push(error)
			}

			expect(errors.length).toBe(0)
			const textChunks = chunks.filter((c) => c.type === "text")
			expect(textChunks.length).toBeGreaterThan(0)
			expect(textChunks[0].text).toBe("Hello")
		})

		it("should format full conversation correctly", async () => {
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_item.added","item":{"type":"text","text":"Response"}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			const gpt5Handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "gpt-5.1",
			})

			const stream = gpt5Handler.createMessage(systemPrompt, messages, {
				taskId: "task1",
			})
			for await (const chunk of stream) {
				// consume
			}

			const callBody = JSON.parse(mockFetch.mock.calls[0][1].body)
			expect(callBody.input).toEqual([
				{
					role: "user",
					content: [{ type: "input_text", text: "Hello!" }],
				},
			])
			expect(callBody.previous_response_id).toBeUndefined()
		})

		it("should provide helpful error messages for different error codes", async () => {
			const testCases = [
				{ status: 400, expectedMessage: "Invalid request to Responses API" },
				{ status: 401, expectedMessage: "Authentication failed" },
				{ status: 403, expectedMessage: "Access denied" },
				{ status: 404, expectedMessage: "Responses API endpoint not found" },
				{ status: 429, expectedMessage: "Rate limit exceeded" },
				{ status: 500, expectedMessage: "OpenAI service error" },
			]

			for (const { status, expectedMessage } of testCases) {
				// Mock fetch with error response
				const mockFetch = vitest.fn().mockResolvedValue({
					ok: false,
					status,
					statusText: "Error",
					text: async () => JSON.stringify({ error: { message: "Test error" } }),
				})
				global.fetch = mockFetch as any

				// Mock SDK to fail
				mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

				handler = new OpenAiNativeHandler({
					...mockOptions,
					apiModelId: "gpt-5.1",
				})

				const stream = handler.createMessage(systemPrompt, messages)

				await expect(async () => {
					for await (const chunk of stream) {
						// Should throw before yielding anything
					}
				}).rejects.toThrow(expectedMessage)

				// Clean up
				delete (global as any).fetch
			}
		})
	})
})

// Additional tests for GPT-5 streaming event coverage
describe("GPT-5 streaming event coverage (additional)", () => {
	afterEach(() => {
		if ((global as any).fetch) {
			delete (global as any).fetch
		}
	})

	it("should handle reasoning delta events for GPT-5", async () => {
		const mockFetch = vitest.fn().mockResolvedValue({
			ok: true,
			body: new ReadableStream({
				start(controller) {
					controller.enqueue(
						new TextEncoder().encode(
							'data: {"type":"response.reasoning.delta","delta":"Thinking about the problem..."}\n\n',
						),
					)
					controller.enqueue(
						new TextEncoder().encode('data: {"type":"response.text.delta","delta":"The answer is..."}\n\n'),
					)
					controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
					controller.close()
				},
			}),
		})
		global.fetch = mockFetch as any

		// Mock SDK to fail
		mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

		const handler = new OpenAiNativeHandler({
			apiModelId: "gpt-5.1",
			openAiNativeApiKey: "test-api-key",
		})

		const systemPrompt = "You are a helpful assistant."
		const messages: Anthropic.Messages.MessageParam[] = [{ role: "user", content: "Hello!" }]
		const stream = handler.createMessage(systemPrompt, messages)

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
		}

		const reasoningChunks = chunks.filter((c) => c.type === "reasoning")
		const textChunks = chunks.filter((c) => c.type === "text")

		expect(reasoningChunks).toHaveLength(1)
		expect(reasoningChunks[0].text).toBe("Thinking about the problem...")
		expect(textChunks).toHaveLength(1)
		expect(textChunks[0].text).toBe("The answer is...")
	})

	it("should handle refusal delta events for GPT-5 and prefix output", async () => {
		const mockFetch = vitest.fn().mockResolvedValue({
			ok: true,
			body: new ReadableStream({
				start(controller) {
					controller.enqueue(
						new TextEncoder().encode(
							'data: {"type":"response.refusal.delta","delta":"I cannot comply with this request."}\n\n',
						),
					)
					controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
					controller.close()
				},
			}),
		})
		global.fetch = mockFetch as any

		// Mock SDK to fail
		mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

		const handler = new OpenAiNativeHandler({
			apiModelId: "gpt-5.1",
			openAiNativeApiKey: "test-api-key",
		})

		const systemPrompt = "You are a helpful assistant."
		const messages: Anthropic.Messages.MessageParam[] = [{ role: "user", content: "Do something disallowed" }]
		const stream = handler.createMessage(systemPrompt, messages)

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
		}

		const textChunks = chunks.filter((c) => c.type === "text")
		expect(textChunks).toHaveLength(1)
		expect(textChunks[0].text).toBe("[Refusal] I cannot comply with this request.")
	})

	it("should ignore malformed JSON lines in SSE stream", async () => {
		const mockFetch = vitest.fn().mockResolvedValue({
			ok: true,
			body: new ReadableStream({
				start(controller) {
					controller.enqueue(
						new TextEncoder().encode(
							'data: {"type":"response.output_item.added","item":{"type":"text","text":"Before"}}\n\n',
						),
					)
					// Malformed JSON line
					controller.enqueue(
						new TextEncoder().encode('data: {"type":"response.text.delta","delta":"Bad"\n\n'),
					)
					// Valid line after malformed
					controller.enqueue(
						new TextEncoder().encode(
							'data: {"type":"response.output_item.added","item":{"type":"text","text":"After"}}\n\n',
						),
					)
					controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
					controller.close()
				},
			}),
		})
		global.fetch = mockFetch as any

		// Mock SDK to fail
		mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

		const handler = new OpenAiNativeHandler({
			apiModelId: "gpt-5.1",
			openAiNativeApiKey: "test-api-key",
		})

		const systemPrompt = "You are a helpful assistant."
		const messages: Anthropic.Messages.MessageParam[] = [{ role: "user", content: "Hello!" }]
		const stream = handler.createMessage(systemPrompt, messages)

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
		}

		// It should not throw and still capture the valid texts around the malformed line
		const textChunks = chunks.filter((c) => c.type === "text")
		expect(textChunks.map((c: any) => c.text)).toEqual(["Before", "After"])
	})

	describe("Codex Mini Model", () => {
		let handler: OpenAiNativeHandler
		const mockOptions: ApiHandlerOptions = {
			openAiNativeApiKey: "test-api-key",
			apiModelId: "codex-mini-latest",
		}

		it("should handle codex-mini-latest streaming response", async () => {
			// Mock fetch for Codex Mini responses API
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						// Codex Mini uses the same responses API format
						controller.enqueue(
							new TextEncoder().encode('data: {"type":"response.output_text.delta","delta":"Hello"}\n\n'),
						)
						controller.enqueue(
							new TextEncoder().encode('data: {"type":"response.output_text.delta","delta":" from"}\n\n'),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_text.delta","delta":" Codex"}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_text.delta","delta":" Mini!"}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.done","response":{"usage":{"prompt_tokens":50,"completion_tokens":10}}}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "codex-mini-latest",
			})

			const systemPrompt = "You are a helpful coding assistant."
			const messages: Anthropic.Messages.MessageParam[] = [
				{ role: "user", content: "Write a hello world function" },
			]

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Verify text chunks
			const textChunks = chunks.filter((c) => c.type === "text")
			expect(textChunks).toHaveLength(4)
			expect(textChunks.map((c) => c.text).join("")).toBe("Hello from Codex Mini!")

			// Verify usage data from API
			const usageChunks = chunks.filter((c) => c.type === "usage")
			expect(usageChunks).toHaveLength(1)
			expect(usageChunks[0]).toMatchObject({
				type: "usage",
				inputTokens: 50,
				outputTokens: 10,
				totalCost: expect.any(Number), // Codex Mini has pricing: $1.5/M input, $6/M output
			})

			// Verify cost is calculated correctly based on API usage data
			const expectedCost = (50 / 1_000_000) * 1.5 + (10 / 1_000_000) * 6
			expect(usageChunks[0].totalCost).toBeCloseTo(expectedCost, 10)

			// Verify the request was made with correct parameters
			expect(mockFetch).toHaveBeenCalledWith(
				"https://api.openai.com/v1/responses",
				expect.objectContaining({
					method: "POST",
					headers: expect.objectContaining({
						"Content-Type": "application/json",
						Authorization: "Bearer test-api-key",
					}),
					body: expect.any(String),
				}),
			)

			const requestBody = JSON.parse(mockFetch.mock.calls[0][1].body)
			expect(requestBody).toMatchObject({
				model: "codex-mini-latest",
				instructions: "You are a helpful coding assistant.",
				input: [
					{
						role: "user",
						content: [{ type: "input_text", text: "Write a hello world function" }],
					},
				],
				stream: true,
			})
		})

		it("should handle codex-mini-latest non-streaming completion", async () => {
			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "codex-mini-latest",
			})

			// Mock the responses.create method to return a non-streaming response
			mockResponsesCreate.mockResolvedValue({
				output: [
					{
						type: "message",
						content: [
							{
								type: "output_text",
								text: "def hello_world():\n    print('Hello, World!')",
							},
						],
					},
				],
			})

			const result = await handler.completePrompt("Write a hello world function in Python")

			expect(result).toBe("def hello_world():\n    print('Hello, World!')")
			expect(mockResponsesCreate).toHaveBeenCalledWith(
				expect.objectContaining({
					model: "codex-mini-latest",
					stream: false,
					store: false,
				}),
				expect.objectContaining({
					signal: expect.any(Object),
				}),
			)
		})

		it("should handle codex-mini-latest API errors", async () => {
			// Mock fetch with error response
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: false,
				status: 429,
				statusText: "Too Many Requests",
				text: async () => "Rate limit exceeded",
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "codex-mini-latest",
			})

			const systemPrompt = "You are a helpful assistant."
			const messages: Anthropic.Messages.MessageParam[] = [{ role: "user", content: "Hello" }]

			const stream = handler.createMessage(systemPrompt, messages)

			// Should throw an error (using the same error format as GPT-5)
			await expect(async () => {
				for await (const chunk of stream) {
					// consume stream
				}
			}).rejects.toThrow("Rate limit exceeded")
		})

		it("should handle codex-mini-latest with multiple user messages", async () => {
			// Mock fetch for streaming response
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_text.delta","delta":"Combined response"}\n\n',
							),
						)
						controller.enqueue(new TextEncoder().encode('data: {"type":"response.completed"}\n\n'))
						controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "codex-mini-latest",
			})

			const systemPrompt = "You are a helpful assistant."
			const messages: Anthropic.Messages.MessageParam[] = [
				{ role: "user", content: "First question" },
				{ role: "assistant", content: "First answer" },
				{ role: "user", content: "Second question" },
			]

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks: any[] = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Verify the request body includes full conversation in structured format (without embedding system prompt)
			const requestBody = JSON.parse(mockFetch.mock.calls[0][1].body)
			expect(requestBody.instructions).toBe("You are a helpful assistant.")
			expect(requestBody.input).toEqual([
				{
					role: "user",
					content: [{ type: "input_text", text: "First question" }],
				},
				{
					role: "assistant",
					content: [{ type: "output_text", text: "First answer" }],
				},
				{
					role: "user",
					content: [{ type: "input_text", text: "Second question" }],
				},
			])
		})

		it("should handle codex-mini-latest stream error events", async () => {
			// Mock fetch with error event in stream
			const mockFetch = vitest.fn().mockResolvedValue({
				ok: true,
				body: new ReadableStream({
					start(controller) {
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.output_text.delta","delta":"Partial"}\n\n',
							),
						)
						controller.enqueue(
							new TextEncoder().encode(
								'data: {"type":"response.error","error":{"message":"Model overloaded"}}\n\n',
							),
						)
						// The error handler will throw, but we still need to close the stream
						controller.close()
					},
				}),
			})
			global.fetch = mockFetch as any

			// Mock SDK to fail
			mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

			handler = new OpenAiNativeHandler({
				...mockOptions,
				apiModelId: "codex-mini-latest",
			})

			const systemPrompt = "You are a helpful assistant."
			const messages: Anthropic.Messages.MessageParam[] = [{ role: "user", content: "Hello" }]

			const stream = handler.createMessage(systemPrompt, messages)

			// Should throw an error when encountering error event
			await expect(async () => {
				const chunks = []
				for await (const chunk of stream) {
					chunks.push(chunk)
				}
			}).rejects.toThrow("Responses API error: Model overloaded")
		})

		// New tests: ensure text.verbosity is omitted for models without supportsVerbosity
		describe("Verbosity gating for non-GPT-5 models", () => {
			it("should omit text.verbosity for gpt-4.1", async () => {
				const mockFetch = vitest.fn().mockResolvedValue({
					ok: true,
					body: new ReadableStream({
						start(controller) {
							controller.enqueue(
								new TextEncoder().encode('data: {"type":"response.done","response":{}}\n\n'),
							)
							controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
							controller.close()
						},
					}),
				})
				;(global as any).fetch = mockFetch as any

				// Force SDK path to fail so we use fetch fallback
				mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

				const handler = new OpenAiNativeHandler({
					apiModelId: "gpt-4.1",
					openAiNativeApiKey: "test-api-key",
					verbosity: "high",
				})

				const systemPrompt = "You are a helpful assistant."
				const messages: Anthropic.Messages.MessageParam[] = [{ role: "user", content: "Hello!" }]
				const stream = handler.createMessage(systemPrompt, messages)

				for await (const _ of stream) {
					// drain
				}

				const bodyStr = (mockFetch.mock.calls[0][1] as any).body as string
				const parsedBody = JSON.parse(bodyStr)
				expect(parsedBody.model).toBe("gpt-4.1")
				expect(parsedBody.text).toBeUndefined()
				expect(bodyStr).not.toContain('"verbosity"')
			})

			it("should omit text.verbosity for gpt-4o", async () => {
				const mockFetch = vitest.fn().mockResolvedValue({
					ok: true,
					body: new ReadableStream({
						start(controller) {
							controller.enqueue(
								new TextEncoder().encode('data: {"type":"response.done","response":{}}\n\n'),
							)
							controller.enqueue(new TextEncoder().encode("data: [DONE]\n\n"))
							controller.close()
						},
					}),
				})
				;(global as any).fetch = mockFetch as any

				// Force SDK path to fail so we use fetch fallback
				mockResponsesCreate.mockRejectedValue(new Error("SDK not available"))

				const handler = new OpenAiNativeHandler({
					apiModelId: "gpt-4o",
					openAiNativeApiKey: "test-api-key",
					verbosity: "low",
				})

				const systemPrompt = "You are a helpful assistant."
				const messages: Anthropic.Messages.MessageParam[] = [{ role: "user", content: "Hello!" }]
				const stream = handler.createMessage(systemPrompt, messages)

				for await (const _ of stream) {
					// drain
				}

				const bodyStr = (mockFetch.mock.calls[0][1] as any).body as string
				const parsedBody = JSON.parse(bodyStr)
				expect(parsedBody.model).toBe("gpt-4o")
				expect(parsedBody.text).toBeUndefined()
				expect(bodyStr).not.toContain('"verbosity"')
			})

 it("processEvent should emit tool_call_partial using pending tool identity and emit fallback tool_call on done", async () => {
   const handler = new OpenAiNativeHandler({
     apiModelId: "gpt-5.1",
     openAiNativeApiKey: "test-api-key",
   } as any)
 
   const model = handler.getModel()
 
   // Step 1: Simulate an output_item.added that sets pending tool identity
   const addedEvent = {
     type: "response.output_item.added",
     item: {
       type: "function_call",
       call_id: "call-1",
       name: "toolA",
     },
   }
   const chunks1: any[] = []
   for await (const c of (handler as any).processEvent(addedEvent, model)) {
     chunks1.push(c)
   }
   // added event doesn't yield a tool chunk, but should set pending identity
   expect((handler as any).pendingToolCallId).toBe("call-1")
   expect((handler as any).pendingToolCallName).toBe("toolA")
   expect(chunks1).toHaveLength(0)
 
   // Step 2: Simulate a tool call arguments delta that lacks id/name - should use pending identity
   const deltaEvent = {
     type: "response.tool_call_arguments.delta",
     // no call_id/name provided to simulate stream that uses pending identity
     delta: '{"param":"value"}',
     index: 2,
   }
   const chunks2: any[] = []
   for await (const c of (handler as any).processEvent(deltaEvent, model)) {
     chunks2.push(c)
   }
 
   expect(chunks2).toHaveLength(1)
   expect(chunks2[0].type).toBe("tool_call_partial")
   expect(chunks2[0].id).toBe("call-1")
   expect(chunks2[0].name).toBe("toolA")
   expect(chunks2[0].index).toBe(2)
   expect(chunks2[0].arguments).toBe('{"param":"value"}')
 
   // The streamedToolCallIds should include call-1 now
   expect((handler as any).streamedToolCallIds.has("call-1")).toBe(true)
 
   // Step 3: Simulate an output_item.done for a different call id that was NOT streamed (fallback)
   const doneEvent = {
     type: "response.output_item.done",
     item: {
       type: "function_call",
       call_id: "call-2",
       name: "toolB",
       arguments: { x: 1, y: 2 },
     },
   }
   const chunks3: any[] = []
   for await (const c of (handler as any).processEvent(doneEvent, model)) {
     chunks3.push(c)
   }
 
   // Should yield a full tool_call for call-2 because it wasn't in streamedToolCallIds
   expect(chunks3).toHaveLength(1)
   expect(chunks3[0].type).toBe("tool_call")
   expect(chunks3[0].id).toBe("call-2")
   expect(chunks3[0].name).toBe("toolB")
   expect(typeof chunks3[0].arguments).toBe("string")
   // arguments must be a JSON string containing the object
   expect(JSON.parse(chunks3[0].arguments)).toEqual({ x: 1, y: 2 })
 })


 it("processEvent should capture response id, service_tier and reasoning encrypted_content", async () => {
   const handler = new OpenAiNativeHandler({
     apiModelId: "gpt-5.1",
     openAiNativeApiKey: "test-api-key",
   } as any)
 
   const model = handler.getModel()
 
   // Construct a fake event with response containing output with reasoning item
   const event = {
     response: {
       service_tier: "flex",
       id: "response-xyz",
       output: [
         {
           type: "reasoning",
           encrypted_content: "ENC_CONTENT_123",
           id: "reasoning-1",
         },
         {
           type: "text",
           content: [
             {
               type: "text",
               text: "Hello!",
             },
           ],
         },
       ],
     },
   }
 
   // Drain the async generator returned by the private processEvent to apply side effects
   const out: any[] = []
   for await (const chunk of (handler as any).processEvent(event, model)) {
     out.push(chunk)
   }
 
   // After processing the event, the handler should have recorded the response id
   expect(handler.getResponseId()).toBe("response-xyz")
 
   // getEncryptedContent should return the encrypted_content and id from the first reasoning item
   const enc = handler.getEncryptedContent()
   expect(enc).toBeDefined()
   expect(enc).toMatchObject({
     encrypted_content: "ENC_CONTENT_123",
     id: "reasoning-1",
   })
 
   // Now set lastResponseOutput to a value without encrypted content to ensure undefined return
   ;(handler as any).lastResponseOutput = [{ type: "reasoning", someField: "no-encrypted" }]
   expect(handler.getEncryptedContent()).toBeUndefined()
 })


 it("buildRequestBody should add additionalProperties:false for MCP and required for regular tools", () => {
   const handler = new OpenAiNativeHandler({
     apiModelId: "gpt-5.1",
     openAiNativeApiKey: "test-api-key",
     // Request flexibility so buildRequestBody may include a tier if present in model.info.tiers
     openAiNativeServiceTier: "flex" as any,
     modelTemperature: 0.7,
   } as any)
 
   // Construct a fake model object to pass into the private buildRequestBody method
   const fakeModel: any = {
     id: "test-model",
     info: {
       supportsTemperature: true,
       supportsVerbosity: true,
       supportsPromptCache: true,
       promptCacheRetention: "24h",
       tiers: [{ name: "flex", inputPrice: 5, outputPrice: 10 }],
     },
     maxTokens: 1000,
   }
 
   // Regular (non-MCP) tool schema - should get `required` set and nested additionalProperties:false
   const regularTool = {
     type: "function",
     function: {
       name: "regular-tool",
       description: "A regular tool",
       parameters: {
         type: "object",
         properties: {
           foo: { type: "string" },
           nested: {
             type: "object",
             properties: {
               inner: { type: "string" },
             },
           },
           arr: {
             type: "array",
             items: {
               type: "object",
               properties: {
                 itemProp: { type: "string" },
               },
             },
           },
         },
       },
     },
   }
 
   // MCP tool - name starts with 'mcp--' and should use ensureAdditionalPropertiesFalse (no required)
   const mcpTool = {
     type: "function",
     function: {
       name: "mcp--external-tool",
       description: "An MCP tool",
       parameters: {
         type: "object",
         properties: {
           a: { type: "string" },
           b: {
             type: "object",
             properties: {
               deep: { type: "string" },
             },
           },
         },
       },
     },
   }
 
   const formattedInput = [
     {
       role: "user",
       content: [{ type: "input_text", text: "Hello" }],
     },
   ]
 
   // Call the private method via any cast
   const body = (handler as any).buildRequestBody(
     fakeModel,
     formattedInput,
     "system prompt",
     "low", // verbosity
     undefined, // reasoning effort
     { tools: [regularTool, mcpTool], parallelToolCalls: true },
   )
 
   // Two tools should be present
   expect(body.tools).toHaveLength(2)
 
   // Regular tool: strict true and required array should be present
   const regularParams = body.tools[0].parameters
   expect(body.tools[0].name).toBe("regular-tool")
   expect(body.tools[0].strict).toBe(true)
   // Top-level properties should have required set to all keys
   expect(Array.isArray(regularParams.required)).toBe(true)
   expect(regularParams.required).toEqual(expect.arrayContaining(["foo", "nested", "arr"]))
   // Nested object should have additionalProperties set to false
   expect(regularParams.properties.nested.additionalProperties).toBe(false)
   // Array items' object should also have additionalProperties:false
   expect(regularParams.properties.arr.items.additionalProperties).toBe(false)
 
   // MCP tool: strict false and no 'required' array should be added
   const mcpParams = body.tools[1].parameters
   expect(body.tools[1].name).toBe("mcp--external-tool")
   expect(body.tools[1].strict).toBe(false)
   // ensureAdditionalPropertiesFalse should add additionalProperties:false but NOT required
   expect(mcpParams.additionalProperties).toBe(false)
   // The MCP path should not add required arrays
   expect(mcpParams.required).toBeUndefined()
   // Nested MCP property should also have additionalProperties:false
   expect(mcpParams.properties.b.additionalProperties).toBe(false)
 
   // Ensure prompt_cache_retention was included as the model info supports it
   expect(body.prompt_cache_retention).toBe("24h")
 
   // Ensure the service_tier was included because options selected a known tier and the model supports it
   expect(body.service_tier).toBe("flex")
 })


 it("should extract encrypted_content and id from lastResponseOutput and return response id", () => {
   const handler = new OpenAiNativeHandler({
     apiModelId: "gpt-5.1",
     openAiNativeApiKey: "test-api-key",
   })
   // Initially, no output
   expect(handler.getEncryptedContent()).toBeUndefined()
   // Inject a lastResponseOutput containing a reasoning item
   ;(handler as any).lastResponseOutput = [
     { type: "text", text: "ignore" },
     { type: "reasoning", encrypted_content: "ENC_DATA", id: "reason-123" },
   ]
   const enc = handler.getEncryptedContent()
   expect(enc).toBeDefined()
   expect(enc?.encrypted_content).toBe("ENC_DATA")
   expect(enc?.id).toBe("reason-123")
   // Test getResponseId behavior
   expect(handler.getResponseId()).toBeUndefined()
   ;(handler as any).lastResponseId = "resp-999"
   expect(handler.getResponseId()).toBe("resp-999")
 })


 it("should apply service tier pricing overrides when tier exists and return original for missing/default tier", () => {
   const handler = new OpenAiNativeHandler({
     apiModelId: "gpt-5.1",
     openAiNativeApiKey: "test-api-key",
   })
   const info = {
     inputPrice: 1,
     outputPrice: 2,
     cacheReadsPrice: 3,
     cacheWritesPrice: 4,
     tiers: [
       { name: "premium", inputPrice: 10, outputPrice: 20, cacheReadsPrice: 30, cacheWritesPrice: 40 },
     ],
   } as any
   const applied = (handler as any).applyServiceTierPricing(info, "premium")
   // Pricing values should be overridden from tier
   expect(applied.inputPrice).toBe(10)
   expect(applied.outputPrice).toBe(20)
   expect(applied.cacheReadsPrice).toBe(30)
   expect(applied.cacheWritesPrice).toBe(40)
   // Default or unknown tier should return original info object (or effectively same values)
   const unchanged = (handler as any).applyServiceTierPricing(info, "default")
   expect(unchanged).toBe(info)
   const unknown = (handler as any).applyServiceTierPricing(info, "nonexistent")
   expect(unknown).toBe(info)
 })


 it("should normalize usage deriving total input tokens, cache reads/writes, reasoning tokens and cost", () => {
   const mockOptions: ApiHandlerOptions = {
     apiModelId: "gpt-5.1",
     openAiNativeApiKey: "test-api-key",
   }
   const handler = new OpenAiNativeHandler(mockOptions)
   const model = handler.getModel()
   // Simulate a usage object missing direct input_tokens but with details
   const usage = {
     input_tokens_details: { cached_tokens: 3, cache_miss_tokens: 7 },
     output_tokens: 5,
     output_tokens_details: { reasoning_tokens: 2 },
     cache_creation_input_tokens: 1,
     cache_read_input_tokens: 3,
   }
   const out = (handler as any).normalizeUsage(usage, model)
   expect(out).toBeDefined()
   // inputTokens derived from cached + cache_miss
   expect(out.inputTokens).toBe(10)
   expect(out.outputTokens).toBe(5)
   expect(out.cacheWriteTokens).toBe(1)
   expect(out.cacheReadTokens).toBe(3)
   expect(out.reasoningTokens).toBe(2)
   expect(typeof out.totalCost).toBe("number")
   expect(out.totalCost).toBeGreaterThanOrEqual(0)
 })


 it("should build request body adding additionalProperties and required correctly for MCP and non-MCP tools", () => {
   const mockOptions: ApiHandlerOptions = {
     apiModelId: "gpt-5.1",
     openAiNativeApiKey: "test-api-key",
   }
   const handler = new OpenAiNativeHandler(mockOptions)
   const model = handler.getModel()
   // A non-MCP tool with nested object schemas that should get `required` arrays added
   const nonMcpTool = {
     type: "function",
     function: {
       name: "mytool",
       description: "Non-MCP tool",
       parameters: {
         type: "object",
         properties: {
           a: {
             type: "object",
             properties: {
               inner: {
                 type: "object",
                 properties: {
                   x: { type: "string" },
                 },
               },
             },
           },
         },
       },
     },
   }
   // An MCP-style tool - should not get `required` arrays added but should get additionalProperties:false
   const mcpTool = {
     type: "function",
     function: {
       name: "mcp--example-tool",
       description: "MCP tool",
       parameters: {
         type: "object",
         properties: {
           b: {
             type: "object",
             properties: {
               y: { type: "string" },
             },
           },
         },
       },
     },
   }
   const formattedInput = [{ role: "user", content: [{ type: "input_text", text: "hi" }] }]
   const body = (handler as any).buildRequestBody(
     model,
     formattedInput,
     "system prompt",
     "medium",
     "low",
     { tools: [nonMcpTool, mcpTool] },
   )
   expect(body).toBeDefined()
   expect(Array.isArray(body.tools)).toBe(true)
   expect(body.tools).toHaveLength(2)
   const nonMcp = body.tools[0]
   const mcp = body.tools[1]
   // Non-MCP should be strict and have required arrays added recursively
   expect(nonMcp.strict).toBe(true)
   expect(nonMcp.name).toBe("mytool")
   expect(nonMcp.parameters).toBeDefined()
   expect(nonMcp.parameters.additionalProperties).toBe(false)
   // Top-level required should include 'a'
   expect(Array.isArray(nonMcp.parameters.required)).toBe(true)
   expect(nonMcp.parameters.required).toContain("a")
   // Nested object 'a' should have required including 'inner'
   expect(nonMcp.parameters.properties?.a?.required).toBeDefined()
   expect(nonMcp.parameters.properties.a.required).toContain("inner")
   // Deep nested 'inner' should have required including 'x'
   expect(nonMcp.parameters.properties.a.properties?.inner?.required).toBeDefined()
   expect(nonMcp.parameters.properties.a.properties.inner.required).toContain("x")
   // MCP tool should be marked non-strict, and additionalProperties:false applied, but required should not be injected
   expect(mcp.strict).toBe(false)
   expect(mcp.name).toBe("mcp--example-tool")
   expect(mcp.parameters.additionalProperties).toBe(false)
   expect(mcp.parameters.required).toBeUndefined()
 })

		})
	})
})
