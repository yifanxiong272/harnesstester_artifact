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

	describe("createMessage", () => {
		it("should stream messages from Ollama", async () => {
			// Mock the chat response as an async generator
			mockChat.mockImplementation(async function* () {
				yield {
					message: { content: "Hello" },
					eval_count: undefined,
					prompt_eval_count: undefined,
				}
				yield {
					message: { content: " world" },
					eval_count: 2,
					prompt_eval_count: 10,
				}
			})

			const systemPrompt = "You are a helpful assistant"
			const messages = [{ role: "user" as const, content: "Hi there" }]

			const stream = handler.createMessage(systemPrompt, messages)
			const results = []

			for await (const chunk of stream) {
				results.push(chunk)
			}

			expect(results).toHaveLength(3)
			expect(results[0]).toEqual({ type: "text", text: "Hello" })
			expect(results[1]).toEqual({ type: "text", text: " world" })
			expect(results[2]).toEqual({ type: "usage", inputTokens: 10, outputTokens: 2 })
		})

		it("should not include num_ctx by default", async () => {
			// Mock the chat response
			mockChat.mockImplementation(async function* () {
				yield { message: { content: "Response" } }
			})

			const stream = handler.createMessage("System", [{ role: "user" as const, content: "Test" }])

			// Consume the stream
			for await (const _ of stream) {
				// consume stream
			}

			// Verify that num_ctx was NOT included in the options
			expect(mockChat).toHaveBeenCalledWith(
				expect.objectContaining({
					options: expect.not.objectContaining({
						num_ctx: expect.anything(),
					}),
				}),
			)
		})

		it("should include num_ctx when explicitly set via ollamaNumCtx", async () => {
			const options: ApiHandlerOptions = {
				apiModelId: "llama2",
				ollamaModelId: "llama2",
				ollamaBaseUrl: "http://localhost:11434",
				ollamaNumCtx: 8192, // Explicitly set num_ctx
			}

			handler = new NativeOllamaHandler(options)

			// Mock the chat response
			mockChat.mockImplementation(async function* () {
				yield { message: { content: "Response" } }
			})

			const stream = handler.createMessage("System", [{ role: "user" as const, content: "Test" }])

			// Consume the stream
			for await (const _ of stream) {
				// consume stream
			}

			// Verify that num_ctx was included with the specified value
			expect(mockChat).toHaveBeenCalledWith(
				expect.objectContaining({
					options: expect.objectContaining({
						num_ctx: 8192,
					}),
				}),
			)
		})

		it("should handle DeepSeek R1 models with reasoning detection", async () => {
			const options: ApiHandlerOptions = {
				apiModelId: "deepseek-r1",
				ollamaModelId: "deepseek-r1",
				ollamaBaseUrl: "http://localhost:11434",
			}

			handler = new NativeOllamaHandler(options)

			// Mock response with thinking tags
			mockChat.mockImplementation(async function* () {
				yield { message: { content: "<think>Let me think" } }
				yield { message: { content: " about this</think>" } }
				yield { message: { content: "The answer is 42" } }
			})

			const stream = handler.createMessage("System", [{ role: "user" as const, content: "Question?" }])
			const results = []

			for await (const chunk of stream) {
				results.push(chunk)
			}

			// Should detect reasoning vs regular text
			expect(results.some((r) => r.type === "reasoning")).toBe(true)
			expect(results.some((r) => r.type === "text")).toBe(true)
		})
	})

	describe("completePrompt", () => {
		it("should complete a prompt without streaming", async () => {
			mockChat.mockResolvedValue({
				message: { content: "This is the response" },
			})

			const result = await handler.completePrompt("Tell me a joke")

			expect(mockChat).toHaveBeenCalledWith({
				model: "llama2",
				messages: [{ role: "user", content: "Tell me a joke" }],
				stream: false,
				options: {
					temperature: 0,
				},
			})
			expect(result).toBe("This is the response")
		})

		it("should not include num_ctx in completePrompt by default", async () => {
			mockChat.mockResolvedValue({
				message: { content: "Response" },
			})

			await handler.completePrompt("Test prompt")

			// Verify that num_ctx was NOT included in the options
			expect(mockChat).toHaveBeenCalledWith(
				expect.objectContaining({
					options: expect.not.objectContaining({
						num_ctx: expect.anything(),
					}),
				}),
			)
		})

		it("should include num_ctx in completePrompt when explicitly set", async () => {
			const options: ApiHandlerOptions = {
				apiModelId: "llama2",
				ollamaModelId: "llama2",
				ollamaBaseUrl: "http://localhost:11434",
				ollamaNumCtx: 4096, // Explicitly set num_ctx
			}

			handler = new NativeOllamaHandler(options)

			mockChat.mockResolvedValue({
				message: { content: "Response" },
			})

			await handler.completePrompt("Test prompt")

			// Verify that num_ctx was included with the specified value
			expect(mockChat).toHaveBeenCalledWith(
				expect.objectContaining({
					options: expect.objectContaining({
						num_ctx: 4096,
					}),
				}),
			)
		})
	})

	describe("error handling", () => {
		it("should handle connection refused errors", async () => {
			const error = new Error("ECONNREFUSED") as any
			error.code = "ECONNREFUSED"
			mockChat.mockRejectedValue(error)

			const stream = handler.createMessage("System", [{ role: "user" as const, content: "Test" }])

			await expect(async () => {
				for await (const _ of stream) {
					// consume stream
				}
			}).rejects.toThrow("Ollama service is not running")
		})

		it("should handle model not found errors", async () => {
			const error = new Error("Not found") as any
			error.status = 404
			mockChat.mockRejectedValue(error)

			const stream = handler.createMessage("System", [{ role: "user" as const, content: "Test" }])

			await expect(async () => {
				for await (const _ of stream) {
					// consume stream
				}
			}).rejects.toThrow("Model llama2 not found in Ollama")
		})
	})

	describe("getModel", () => {
		it("should return the configured model", () => {
			const model = handler.getModel()
			expect(model.id).toBe("llama2")
			expect(model.info).toBeDefined()
		})
	})

	describe("tool calling", () => {
		it("should include tools when tools are provided", async () => {
			// Model metadata should not gate tool inclusion; metadata.tools controls it.
			mockGetOllamaModels.mockResolvedValue({
				"llama3.2": {
					contextWindow: 128000,
					maxTokens: 4096,
					supportsImages: true,
					supportsPromptCache: false,
				},
			})

			const options: ApiHandlerOptions = {
				apiModelId: "llama3.2",
				ollamaModelId: "llama3.2",
				ollamaBaseUrl: "http://localhost:11434",
			}

			handler = new NativeOllamaHandler(options)

			// Mock the chat response
			mockChat.mockImplementation(async function* () {
				yield { message: { content: "I will use the tool" } }
			})

			const tools = [
				{
					type: "function" as const,
					function: {
						name: "get_weather",
						description: "Get the weather for a location",
						parameters: {
							type: "object",
							properties: {
								location: { type: "string", description: "The city name" },
							},
							required: ["location"],
						},
					},
				},
			]

			const stream = handler.createMessage(
				"System",
				[{ role: "user" as const, content: "What's the weather?" }],
				{ taskId: "test", tools },
			)

			// Consume the stream
			for await (const _ of stream) {
				// consume stream
			}

			// Verify tools were passed to the API
			expect(mockChat).toHaveBeenCalledWith(
				expect.objectContaining({
					tools: [
						{
							type: "function",
							function: {
								name: "get_weather",
								description: "Get the weather for a location",
								parameters: {
									type: "object",
									properties: {
										location: { type: "string", description: "The city name" },
									},
									required: ["location"],
								},
							},
						},
					],
				}),
			)
		})

		it("should include tools even when model metadata doesn't advertise tool support", async () => {
			// Model metadata should not gate tool inclusion; metadata.tools controls it.
			mockGetOllamaModels.mockResolvedValue({
				llama2: {
					contextWindow: 4096,
					maxTokens: 4096,
					supportsImages: false,
					supportsPromptCache: false,
				},
			})

			// Mock the chat response
			mockChat.mockImplementation(async function* () {
				yield { message: { content: "Response without tools" } }
			})

			const tools = [
				{
					type: "function" as const,
					function: {
						name: "get_weather",
						description: "Get the weather",
						parameters: { type: "object", properties: {} },
					},
				},
			]

			const stream = handler.createMessage("System", [{ role: "user" as const, content: "Test" }], {
				taskId: "test",
				tools,
			})

			// Consume the stream
			for await (const _ of stream) {
				// consume stream
			}

			// Verify tools were passed
			expect(mockChat).toHaveBeenCalledWith(
				expect.objectContaining({
					tools: expect.any(Array),
				}),
			)
		})

		it("should not include tools when no tools are provided", async () => {
			// Model metadata should not gate tool inclusion; metadata.tools controls it.
			mockGetOllamaModels.mockResolvedValue({
				"llama3.2": {
					contextWindow: 128000,
					maxTokens: 4096,
					supportsImages: true,
					supportsPromptCache: false,
				},
			})

			const options: ApiHandlerOptions = {
				apiModelId: "llama3.2",
				ollamaModelId: "llama3.2",
				ollamaBaseUrl: "http://localhost:11434",
			}

			handler = new NativeOllamaHandler(options)

			// Mock the chat response
			mockChat.mockImplementation(async function* () {
				yield { message: { content: "Response" } }
			})

			const stream = handler.createMessage("System", [{ role: "user" as const, content: "Test" }], {
				taskId: "test",
			})

			// Consume the stream
			for await (const _ of stream) {
				// consume stream
			}

			// Verify tools were NOT passed
			expect(mockChat).toHaveBeenCalledWith(
				expect.not.objectContaining({
					tools: expect.anything(),
				}),
			)
		})

		it("should yield tool_call_partial when model returns tool calls", async () => {
			// Model metadata should not gate tool inclusion; metadata.tools controls it.
			mockGetOllamaModels.mockResolvedValue({
				"llama3.2": {
					contextWindow: 128000,
					maxTokens: 4096,
					supportsImages: true,
					supportsPromptCache: false,
				},
			})

			const options: ApiHandlerOptions = {
				apiModelId: "llama3.2",
				ollamaModelId: "llama3.2",
				ollamaBaseUrl: "http://localhost:11434",
			}

			handler = new NativeOllamaHandler(options)

			// Mock the chat response with tool calls
			mockChat.mockImplementation(async function* () {
				yield {
					message: {
						content: "",
						tool_calls: [
							{
								function: {
									name: "get_weather",
									arguments: { location: "San Francisco" },
								},
							},
						],
					},
				}
			})

			const tools = [
				{
					type: "function" as const,
					function: {
						name: "get_weather",
						description: "Get the weather for a location",
						parameters: {
							type: "object",
							properties: {
								location: { type: "string" },
							},
							required: ["location"],
						},
					},
				},
			]

			const stream = handler.createMessage(
				"System",
				[{ role: "user" as const, content: "What's the weather in SF?" }],
				{ taskId: "test", tools },
			)

			const results = []
			for await (const chunk of stream) {
				results.push(chunk)
			}

			// Should yield a tool_call_partial chunk
			const toolCallChunk = results.find((r) => r.type === "tool_call_partial")
			expect(toolCallChunk).toBeDefined()
			expect(toolCallChunk).toEqual({
				type: "tool_call_partial",
				index: 0,
				id: "ollama-tool-0",
				name: "get_weather",
				arguments: JSON.stringify({ location: "San Francisco" }),
			})
		})

		it("should yield tool_call_end events after tool_call_partial chunks", async () => {
			// Model metadata should not gate tool inclusion; metadata.tools controls it.
			mockGetOllamaModels.mockResolvedValue({
				"llama3.2": {
					contextWindow: 128000,
					maxTokens: 4096,
					supportsImages: true,
					supportsPromptCache: false,
				},
			})

			const options: ApiHandlerOptions = {
				apiModelId: "llama3.2",
				ollamaModelId: "llama3.2",
				ollamaBaseUrl: "http://localhost:11434",
			}

			handler = new NativeOllamaHandler(options)

			// Mock the chat response with multiple tool calls
			mockChat.mockImplementation(async function* () {
				yield {
					message: {
						content: "",
						tool_calls: [
							{
								function: {
									name: "get_weather",
									arguments: { location: "San Francisco" },
								},
							},
							{
								function: {
									name: "get_time",
									arguments: { timezone: "PST" },
								},
							},
						],
					},
				}
			})

			const tools = [
				{
					type: "function" as const,
					function: {
						name: "get_weather",
						description: "Get the weather for a location",
						parameters: {
							type: "object",
							properties: { location: { type: "string" } },
							required: ["location"],
						},
					},
				},
				{
					type: "function" as const,
					function: {
						name: "get_time",
						description: "Get the current time in a timezone",
						parameters: {
							type: "object",
							properties: { timezone: { type: "string" } },
							required: ["timezone"],
						},
					},
				},
			]

			const stream = handler.createMessage(
				"System",
				[{ role: "user" as const, content: "What's the weather and time in SF?" }],
				{ taskId: "test", tools },
			)

			const results = []
			for await (const chunk of stream) {
				results.push(chunk)
			}

			// Should yield tool_call_partial chunks
			const toolCallPartials = results.filter((r) => r.type === "tool_call_partial")
			expect(toolCallPartials).toHaveLength(2)

			// Should yield tool_call_end events for each tool call
			const toolCallEnds = results.filter((r) => r.type === "tool_call_end")
			expect(toolCallEnds).toHaveLength(2)
			expect(toolCallEnds[0]).toEqual({ type: "tool_call_end", id: "ollama-tool-0" })
			expect(toolCallEnds[1]).toEqual({ type: "tool_call_end", id: "ollama-tool-1" })

			// tool_call_end should come after tool_call_partial
			// Find the last tool_call_partial index
			let lastPartialIndex = -1
			for (let i = results.length - 1; i >= 0; i--) {
				if (results[i].type === "tool_call_partial") {
					lastPartialIndex = i
					break
				}
			}
			const firstEndIndex = results.findIndex((r) => r.type === "tool_call_end")
			expect(firstEndIndex).toBeGreaterThan(lastPartialIndex)
		})

 it("converts assistant-only image parts into empty assistant content", async () => {
   // Ensure chat does not actually stream any chunks
   mockChat.mockImplementationOnce(async function* () {
     // no chunks required for this test
   })
 
   const systemPrompt = "System"
   // Simulate an assistant message that contains only an image block
   const anthropicMessages = [
     {
       role: "assistant" as const,
       content: [
         {
           type: "image",
           source: { type: "base64", data: "BASE64_IMG_ONLY" },
         },
       ],
     },
   ]
 
   const stream = handler.createMessage(systemPrompt, anthropicMessages)
   // consume stream fully (no chunks expected)
   for await (const _ of stream) {
     // consume
   }
 
   // Verify that the Ollama chat was called and that the assistant message content is the empty string
   expect(mockChat).toHaveBeenCalled()
   const callArg = mockChat.mock.calls[0][0]
   const assistantMsg = callArg.messages.find((m: any) => m.role === "assistant")
   expect(assistantMsg).toBeDefined()
   // Per implementation, image parts for assistant are converted to "" and joined -> here result should be ""
   expect(assistantMsg.content).toBe("")
 })


 it("wraps Error instances and rethrows non-Error values from completePrompt", async () => {
   // First, simulate the client.chat rejecting with an Error instance
   mockChat.mockRejectedValueOnce(new Error("boom"))
   await expect(handler.completePrompt("prompt")).rejects.toThrow("Ollama completion error: boom")
 
   // Next, simulate the client.chat rejecting with a non-Error value (e.g., a string)
   mockChat.mockRejectedValueOnce("string error")
   await expect(handler.completePrompt("prompt")).rejects.toEqual("string error")
 })


 it("wraps Ollama constructor errors into a clearer Error message", async () => {
   // Make the mocked Ollama constructor throw only for this test
   const { Ollama } = await import("ollama")
   ;(Ollama as any).mockImplementationOnce(() => {
     throw new Error("constructor fail")
   })
 
   const options = {
     apiModelId: "llama2",
     ollamaModelId: "llama2",
     ollamaBaseUrl: "http://localhost:11434",
   }
   const localHandler = new NativeOllamaHandler(options)
 
   // completePrompt triggers ensureClient (and therefore the constructor)
   await expect(localHandler.completePrompt("hi")).rejects.toThrow(
     "Error creating Ollama client: constructor fail",
   )
 })


 it("converts tool_result string content into an Ollama user message", async () => {
   // Make the chat call succeed but yield nothing so createMessage proceeds to inspect the request
   mockChat.mockImplementationOnce(async function* () {
     // no chunks
   })
 
   const systemPrompt = "System prompt"
   // Simulate an Anthropic user message that contains a tool_result whose content is a simple string
   const anthropicMessages = [
     {
       role: "user" as const,
       content: [
         {
           type: "tool_result",
           // Direct string content should be handled by the typeof === "string" branch
           content: "TOOL_OUTPUT_AS_STRING",
         },
         {
           type: "text",
           text: "Follow-up text",
         },
       ],
     },
   ]
 
   const stream = handler.createMessage(systemPrompt, anthropicMessages)
   // consume the stream (no yields expected)
   for await (const _ of stream) {
     // noop
   }
 
   // Inspect the parameters passed to the Ollama client chat call
   expect(mockChat).toHaveBeenCalled()
   const callArg = mockChat.mock.calls[0][0]
   // There should be a user message that contains the tool result string content
   const userMessages = callArg.messages.filter((m: any) => m.role === "user")
   expect(userMessages.some((m: any) => m.content === "TOOL_OUTPUT_AS_STRING")).toBe(true)
 })


 it("should wrap errors thrown while processing the stream", async () => {
   // Mock the chat to produce one valid chunk then throw when iterating further
   mockChat.mockImplementation(async function* () {
     yield { message: { content: "first" } }
     throw new Error("boom")
   })
 
   const stream = handler.createMessage("System", [{ role: "user" as const, content: "Test" }])
   await expect(async () => {
     for await (const _ of stream) {
       // consume
     }
   }).rejects.toThrow("Ollama stream processing error: boom")
 })


 it("should convert assistant tool_use blocks to Ollama tool_calls", async () => {
   // Mock chat to yield a single chunk so createMessage completes
   mockChat.mockImplementation(async function* () {
     yield { message: { content: "ok" } }
   })
 
   const systemPrompt = "System"
   const messages = [
     {
       role: "assistant" as const,
       content: [
         { type: "text", text: "assistant text" },
         {
           type: "tool_use",
           name: "do_something",
           input: { foo: "bar" },
         },
       ],
     },
   ]
 
   const stream = handler.createMessage(systemPrompt, messages)
   // Consume stream to trigger chat call
   for await (const _ of stream) {
     // noop
   }
 
   expect(mockChat).toHaveBeenCalled()
   const callArg = mockChat.mock.calls[0][0]
   // System + assistant => assistant should be at index 1
   const assistantMsg = callArg.messages[1]
   expect(assistantMsg).toBeDefined()
   expect(assistantMsg.role).toBe("assistant")
   // assistant text should be included
   expect(assistantMsg.content).toContain("assistant text")
   // tool_calls should be present and include the function name and arguments
   expect(assistantMsg.tool_calls).toBeDefined()
   expect(assistantMsg.tool_calls[0]).toMatchObject({
     function: {
       name: "do_something",
       arguments: { foo: "bar" },
     },
   })
 })


 it("should convert user tool_result and images into Ollama messages", async () => {
   // Mock chat to yield a single chunk so createMessage completes
   mockChat.mockImplementation(async function* () {
     yield { message: { content: "ok" } }
   })
 
   const systemPrompt = "SystemPrompt"
   const messages = [
     {
       role: "user" as const,
       content: [
         // Tool result block containing text and an image (base64)
         {
           type: "tool_result",
           content: [
             { type: "text", text: "tool text" },
             { type: "image", source: { type: "base64", data: "BASE64_IMG1" } },
           ],
         },
         // Normal text block
         { type: "text", text: "normal text" },
         // Image block that should become a separate user message image
         { type: "image", source: { type: "base64", data: "BASE64_IMG2" } },
       ],
     },
   ]
 
   const stream = handler.createMessage(systemPrompt, messages)
   // Consume stream to trigger chat call
   for await (const _ of stream) {
     // noop
   }
 
   // Ensure chat was called and captured messages include the converted tool_result and non-tool messages
   expect(mockChat).toHaveBeenCalled()
   const callArg = mockChat.mock.calls[0][0]
   expect(callArg).toBeDefined()
   // The first message is system, second is the tool_result mapped user message, third is the non-tool user message
   expect(callArg.messages[0]).toMatchObject({ role: "system", content: "SystemPrompt" })
   expect(callArg.messages[1]).toMatchObject({
     role: "user",
     // Should include the tool text in the content and include the base64 image from the tool result
     content: expect.stringContaining("tool text"),
     images: ["BASE64_IMG1"],
   })
   expect(callArg.messages[2]).toMatchObject({
     role: "user",
     content: "normal text",
     images: ["BASE64_IMG2"],
   })
 })

	})
})
