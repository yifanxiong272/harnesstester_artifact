import type { Mock } from "vitest"

// Mocks must come first, before imports
vi.mock("vscode", () => {
	class MockLanguageModelTextPart {
		type = "text"
		constructor(public value: string) {}
	}

	class MockLanguageModelToolCallPart {
		type = "tool_call"
		constructor(
			public callId: string,
			public name: string,
			public input: any,
		) {}
	}

	return {
		workspace: {
			onDidChangeConfiguration: vi.fn((_callback) => ({
				dispose: vi.fn(),
			})),
		},
		CancellationTokenSource: vi.fn(() => ({
			token: {
				isCancellationRequested: false,
				onCancellationRequested: vi.fn(),
			},
			cancel: vi.fn(),
			dispose: vi.fn(),
		})),
		CancellationError: class CancellationError extends Error {
			constructor() {
				super("Operation cancelled")
				this.name = "CancellationError"
			}
		},
		LanguageModelChatMessage: {
			Assistant: vi.fn((content) => ({
				role: "assistant",
				content: Array.isArray(content) ? content : [new MockLanguageModelTextPart(content)],
			})),
			User: vi.fn((content) => ({
				role: "user",
				content: Array.isArray(content) ? content : [new MockLanguageModelTextPart(content)],
			})),
		},
		LanguageModelTextPart: MockLanguageModelTextPart,
		LanguageModelToolCallPart: MockLanguageModelToolCallPart,
		lm: {
			selectChatModels: vi.fn(),
		},
	}
})

import * as vscode from "vscode"
import { VsCodeLmHandler } from "../vscode-lm"
import type { ApiHandlerOptions } from "../../../shared/api"
import type { Anthropic } from "@anthropic-ai/sdk"
import { getVsCodeLmModels } from "../vscode-lm"

const mockLanguageModelChat = {
	id: "test-model",
	name: "Test Model",
	vendor: "test-vendor",
	family: "test-family",
	version: "1.0",
	maxInputTokens: 4096,
	sendRequest: vi.fn(),
	countTokens: vi.fn(),
}

describe("VsCodeLmHandler", () => {
	let handler: VsCodeLmHandler
	const defaultOptions: ApiHandlerOptions = {
		vsCodeLmModelSelector: {
			vendor: "test-vendor",
			family: "test-family",
		},
	}

	beforeEach(() => {
		vi.clearAllMocks()
		handler = new VsCodeLmHandler(defaultOptions)
	})

	afterEach(() => {
		handler.dispose()
	})

	describe("constructor", () => {
		it("should initialize with provided options", () => {
			expect(handler).toBeDefined()
			expect(vscode.workspace.onDidChangeConfiguration).toHaveBeenCalled()
		})

		it("should handle configuration changes", () => {
			const callback = (vscode.workspace.onDidChangeConfiguration as Mock).mock.calls[0][0]
			callback({ affectsConfiguration: () => true })
			// Should reset client when config changes
			expect(handler["client"]).toBeNull()
		})
	})

	describe("createClient", () => {
		it("should create client with selector", async () => {
			const mockModel = { ...mockLanguageModelChat }
			;(vscode.lm.selectChatModels as Mock).mockResolvedValueOnce([mockModel])

			const client = await handler["createClient"]({
				vendor: "test-vendor",
				family: "test-family",
			})

			expect(client).toBeDefined()
			expect(client.id).toBe("test-model")
			expect(vscode.lm.selectChatModels).toHaveBeenCalledWith({
				vendor: "test-vendor",
				family: "test-family",
			})
		})

		it("should return default client when no models available", async () => {
			;(vscode.lm.selectChatModels as Mock).mockResolvedValueOnce([])

			const client = await handler["createClient"]({})

			expect(client).toBeDefined()
			expect(client.id).toBe("default-lm")
			expect(client.vendor).toBe("vscode")
		})
	})

	describe("createMessage", () => {
		beforeEach(() => {
			const mockModel = { ...mockLanguageModelChat }
			;(vscode.lm.selectChatModels as Mock).mockResolvedValueOnce([mockModel])
			mockLanguageModelChat.countTokens.mockResolvedValue(10)

			// Override the default client with our test client
			handler["client"] = mockLanguageModelChat
		})

		it("should stream text responses", async () => {
			const systemPrompt = "You are a helpful assistant"
			const messages: Anthropic.Messages.MessageParam[] = [
				{
					role: "user" as const,
					content: "Hello",
				},
			]

			const responseText = "Hello! How can I help you?"
			mockLanguageModelChat.sendRequest.mockResolvedValueOnce({
				stream: (async function* () {
					yield new vscode.LanguageModelTextPart(responseText)
					return
				})(),
				text: (async function* () {
					yield responseText
					return
				})(),
			})

			const stream = handler.createMessage(systemPrompt, messages)
			const chunks = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			expect(chunks).toHaveLength(2) // Text chunk + usage chunk
			expect(chunks[0]).toEqual({
				type: "text",
				text: responseText,
			})
			expect(chunks[1]).toMatchObject({
				type: "usage",
				inputTokens: expect.any(Number),
				outputTokens: expect.any(Number),
			})
		})

		it("should emit tool_call chunks when tools are provided", async () => {
			const systemPrompt = "You are a helpful assistant"
			const messages: Anthropic.Messages.MessageParam[] = [
				{
					role: "user" as const,
					content: "Calculate 2+2",
				},
			]

			const toolCallData = {
				name: "calculator",
				arguments: { operation: "add", numbers: [2, 2] },
				callId: "call-1",
			}

			mockLanguageModelChat.sendRequest.mockResolvedValueOnce({
				stream: (async function* () {
					yield new vscode.LanguageModelToolCallPart(
						toolCallData.callId,
						toolCallData.name,
						toolCallData.arguments,
					)
					return
				})(),
				text: (async function* () {
					yield JSON.stringify({ type: "tool_call", ...toolCallData })
					return
				})(),
			})

			const tools = [
				{
					type: "function" as const,
					function: {
						name: "calculator",
						description: "A simple calculator",
						parameters: {
							type: "object",
							properties: {
								operation: { type: "string" },
								numbers: { type: "array", items: { type: "number" } },
							},
						},
					},
				},
			]

			const stream = handler.createMessage(systemPrompt, messages, {
				taskId: "test-task",
				tools,
			})
			const chunks = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			expect(chunks).toHaveLength(2) // Tool call chunk + usage chunk
			expect(chunks[0]).toEqual({
				type: "tool_call",
				id: toolCallData.callId,
				name: toolCallData.name,
				arguments: JSON.stringify(toolCallData.arguments),
			})
		})

		it("should handle native tool calls when tools are provided", async () => {
			const systemPrompt = "You are a helpful assistant"
			const messages: Anthropic.Messages.MessageParam[] = [
				{
					role: "user" as const,
					content: "Calculate 2+2",
				},
			]

			const toolCallData = {
				name: "calculator",
				arguments: { operation: "add", numbers: [2, 2] },
				callId: "call-1",
			}

			const tools = [
				{
					type: "function" as const,
					function: {
						name: "calculator",
						description: "A simple calculator",
						parameters: {
							type: "object",
							properties: {
								operation: { type: "string" },
								numbers: { type: "array", items: { type: "number" } },
							},
						},
					},
				},
			]

			mockLanguageModelChat.sendRequest.mockResolvedValueOnce({
				stream: (async function* () {
					yield new vscode.LanguageModelToolCallPart(
						toolCallData.callId,
						toolCallData.name,
						toolCallData.arguments,
					)
					return
				})(),
				text: (async function* () {
					yield JSON.stringify({ type: "tool_call", ...toolCallData })
					return
				})(),
			})

			const stream = handler.createMessage(systemPrompt, messages, {
				taskId: "test-task",
				tools,
			})
			const chunks = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			expect(chunks).toHaveLength(2) // Tool call chunk + usage chunk
			expect(chunks[0]).toEqual({
				type: "tool_call",
				id: toolCallData.callId,
				name: toolCallData.name,
				arguments: JSON.stringify(toolCallData.arguments),
			})
		})

		it("should pass tools to request options when tools are provided", async () => {
			const systemPrompt = "You are a helpful assistant"
			const messages: Anthropic.Messages.MessageParam[] = [
				{
					role: "user" as const,
					content: "Calculate 2+2",
				},
			]

			const tools = [
				{
					type: "function" as const,
					function: {
						name: "calculator",
						description: "A simple calculator",
						parameters: {
							type: "object",
							properties: {
								operation: { type: "string" },
							},
						},
					},
				},
			]

			mockLanguageModelChat.sendRequest.mockResolvedValueOnce({
				stream: (async function* () {
					yield new vscode.LanguageModelTextPart("Result: 4")
					return
				})(),
				text: (async function* () {
					yield "Result: 4"
					return
				})(),
			})

			const stream = handler.createMessage(systemPrompt, messages, {
				taskId: "test-task",
				tools,
			})
			const chunks = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			// Verify sendRequest was called with tools in options
			// Note: normalizeToolSchema adds additionalProperties: false for JSON Schema 2020-12 compliance
			expect(mockLanguageModelChat.sendRequest).toHaveBeenCalledWith(
				expect.any(Array),
				expect.objectContaining({
					tools: [
						{
							name: "calculator",
							description: "A simple calculator",
							inputSchema: {
								type: "object",
								properties: {
									operation: { type: "string" },
								},
								additionalProperties: false,
							},
						},
					],
				}),
				expect.anything(),
			)
		})

		it("should handle errors", async () => {
			const systemPrompt = "You are a helpful assistant"
			const messages: Anthropic.Messages.MessageParam[] = [
				{
					role: "user" as const,
					content: "Hello",
				},
			]

			mockLanguageModelChat.sendRequest.mockRejectedValueOnce(new Error("API Error"))

			await expect(handler.createMessage(systemPrompt, messages).next()).rejects.toThrow("API Error")
		})
	})

	describe("getModel", () => {
		it("should return model info when client exists", async () => {
			const mockModel = { ...mockLanguageModelChat }
			// The handler starts async initialization in the constructor.
			// Make the test deterministic by explicitly (re)initializing here.
			;(vscode.lm.selectChatModels as Mock).mockResolvedValue([mockModel])
			handler["client"] = null
			await handler.initializeClient()

			const model = handler.getModel()
			expect(model.id).toBe("test-model")
			expect(model.info).toBeDefined()
			expect(model.info.contextWindow).toBe(4096)
		})

		it("should return fallback model info when no client exists", () => {
			// Clear the client first
			handler["client"] = null
			const model = handler.getModel()
			expect(model.id).toBe("test-vendor/test-family")
			expect(model.info).toBeDefined()
		})

		it("should return basic model info when client exists", async () => {
			const mockModel = { ...mockLanguageModelChat }
			// The handler starts async initialization in the constructor.
			// Make the test deterministic by explicitly (re)initializing here.
			;(vscode.lm.selectChatModels as Mock).mockResolvedValue([mockModel])
			handler["client"] = null
			await handler.initializeClient()

			const model = handler.getModel()
			expect(model.info).toBeDefined()
			expect(model.info.contextWindow).toBe(4096)
		})

		it("should return fallback model info when no client exists", () => {
			// Clear the client first
			handler["client"] = null
			const model = handler.getModel()
			expect(model.info).toBeDefined()
		})
	})

	describe("countTokens", () => {
		beforeEach(() => {
			handler["client"] = mockLanguageModelChat
		})

		it("should count tokens when called outside of an active request", async () => {
			// Ensure no active request cancellation token exists
			handler["currentRequestCancellation"] = null

			mockLanguageModelChat.countTokens.mockResolvedValueOnce(42)

			const content: Anthropic.Messages.ContentBlockParam[] = [{ type: "text", text: "Hello world" }]
			const result = await handler.countTokens(content)

			expect(result).toBe(42)
			expect(mockLanguageModelChat.countTokens).toHaveBeenCalledWith("Hello world", expect.any(Object))
		})

		it("should count tokens when called during an active request", async () => {
			// Simulate an active request with a cancellation token
			const mockCancellation = {
				token: { isCancellationRequested: false, onCancellationRequested: vi.fn() },
				cancel: vi.fn(),
				dispose: vi.fn(),
			}
			handler["currentRequestCancellation"] = mockCancellation as any

			mockLanguageModelChat.countTokens.mockResolvedValueOnce(50)

			const content: Anthropic.Messages.ContentBlockParam[] = [{ type: "text", text: "Test content" }]
			const result = await handler.countTokens(content)

			expect(result).toBe(50)
			expect(mockLanguageModelChat.countTokens).toHaveBeenCalledWith("Test content", mockCancellation.token)
		})

		it("should return 0 when no client is available", async () => {
			handler["client"] = null
			handler["currentRequestCancellation"] = null

			const content: Anthropic.Messages.ContentBlockParam[] = [{ type: "text", text: "Hello" }]
			const result = await handler.countTokens(content)

			expect(result).toBe(0)
		})

		it("should handle image blocks with placeholder", async () => {
			handler["currentRequestCancellation"] = null
			mockLanguageModelChat.countTokens.mockResolvedValueOnce(5)

			const content: Anthropic.Messages.ContentBlockParam[] = [
				{ type: "image", source: { type: "base64", media_type: "image/png", data: "abc" } },
			]
			const result = await handler.countTokens(content)

			expect(result).toBe(5)
			expect(mockLanguageModelChat.countTokens).toHaveBeenCalledWith("[IMAGE]", expect.any(Object))
		})
	})

	describe("completePrompt", () => {
		it("should complete single prompt", async () => {
			const mockModel = { ...mockLanguageModelChat }
			;(vscode.lm.selectChatModels as Mock).mockResolvedValueOnce([mockModel])

			const responseText = "Completed text"
			mockLanguageModelChat.sendRequest.mockResolvedValueOnce({
				stream: (async function* () {
					yield new vscode.LanguageModelTextPart(responseText)
					return
				})(),
				text: (async function* () {
					yield responseText
					return
				})(),
			})

			// Override the default client with our test client to ensure it uses
			// the mock implementation rather than the default fallback
			handler["client"] = mockLanguageModelChat

			const result = await handler.completePrompt("Test prompt")
			expect(result).toBe(responseText)
			expect(mockLanguageModelChat.sendRequest).toHaveBeenCalled()
		})

		it("should handle errors during completion", async () => {
			const mockModel = { ...mockLanguageModelChat }
			;(vscode.lm.selectChatModels as Mock).mockResolvedValueOnce([mockModel])

			mockLanguageModelChat.sendRequest.mockRejectedValueOnce(new Error("Completion failed"))

			// Make sure we're using the mock client
			handler["client"] = mockLanguageModelChat

			const promise = handler.completePrompt("Test prompt")
			await expect(promise).rejects.toThrow("VSCode LM completion error: Completion failed")
		})
	})

  it("getModel warns on missing client properties and completePrompt rethrows non-Error rejections", async () => {
    // Setup a client with some missing properties to trigger the warning branch
    handler["client"] = {
      id: "my-model",
      vendor: undefined,
      family: undefined,
      version: undefined,
      maxInputTokens: -10, // negative should be clamped to 0 for contextWindow
    } as any
  
    const model = handler.getModel()
    expect(model.id).toBe("my-model")
    // negative maxInputTokens should turn into contextWindow 0
    expect(model.info.contextWindow).toBe(0)
  
    // completePrompt: ensure non-Error rejection is rethrown as-is
    mockLanguageModelChat.sendRequest.mockRejectedValueOnce("raw-string-error")
    handler["client"] = mockLanguageModelChat
    await expect(handler.completePrompt("prompt")).rejects.toBe("raw-string-error")
  })


  it("createMessage handles CancellationError and object errors from the response stream", async () => {
    // Ensure the handler uses our mock client
    handler["client"] = mockLanguageModelChat
    const systemPrompt = "You are a test assistant"
    const messages = [{ role: "user" as const, content: "Hello" }]
  
    // CancellationError path
    mockLanguageModelChat.sendRequest.mockRejectedValueOnce(new vscode.CancellationError())
    await expect(handler.createMessage(systemPrompt, messages).next()).rejects.toThrow(
      "Roo Code <Language Model API>: Request cancelled by user",
    )
  
    // Object error path (non-Error object)
    const errObj = { code: 123, message: "boom" }
    mockLanguageModelChat.sendRequest.mockRejectedValueOnce(errObj)
    await expect(handler.createMessage(systemPrompt, messages).next()).rejects.toThrow(
      /Roo Code <Language Model API>: Response stream error:/,
    )
  })


  it("initializeClient returns early when client exists and throws when createClient rejects", async () => {
    // Ensure handler starts with a client - initializeClient should return early
    handler["client"] = { id: "already-initialized" } as any
    await expect(handler.initializeClient()).resolves.toBeUndefined()
  
    // Now force createClient to fail for the next call and ensure initializeClient surfaces the error
    handler["client"] = null
    const spy = vi
      .spyOn(handler as any, "createClient")
      .mockRejectedValueOnce(new Error("init failure"))
  
    await expect(handler.initializeClient()).rejects.toThrow(/init failure|Failed to initialize client/)
  
    spy.mockRestore()
  })


  it("createMessage skips invalid tool calls and unknown chunks", async () => {
    // Use the mock client and prepare its sendRequest to emit invalid tool calls and an unknown chunk
    handler["client"] = mockLanguageModelChat
  
    mockLanguageModelChat.sendRequest.mockResolvedValueOnce({
      stream: (async function* () {
        // invalid tool name (null)
        yield new vscode.LanguageModelToolCallPart(null as any, "name", { a: 1 })
        // invalid tool callId (null)
        yield new vscode.LanguageModelToolCallPart("call1", null as any, { a: 1 })
        // invalid tool input (not an object)
        yield new vscode.LanguageModelToolCallPart("call2", "name2", "not-an-object" as any)
        // unknown chunk type
        yield {} as any
        return
      })(),
      text: (async function* () {
        yield ""
        return
      })(),
    })
  
    const stream = handler.createMessage(
      "sys-prompt",
      [{ role: "user" as const, content: "hi" }],
      {
        taskId: "t",
        tools: [
          {
            type: "function" as const,
            function: {
              name: "name",
              description: "desc",
              parameters: { type: "object" },
            },
          },
        ],
      },
    )
  
    const chunks: any[] = []
    for await (const c of stream) {
      chunks.push(c)
    }
  
    // All invalid chunks and unknown chunk types should be skipped,
    // so only the final usage chunk should be present.
    expect(chunks.length).toBe(1)
    expect(chunks[0]).toMatchObject({ type: "usage" })
  })


  it("internalCountTokens handles empty chat messages, non-numeric, negative and cancellation errors", async () => {
    // Ensure the handler has a mock client
    handler["client"] = mockLanguageModelChat
  
    // 1) Non-numeric token count returned
    mockLanguageModelChat.countTokens.mockResolvedValueOnce("not-a-number" as any)
    expect(await handler["internalCountTokens"]("hello")).toBe(0)
  
    // 2) Negative token count
    mockLanguageModelChat.countTokens.mockResolvedValueOnce(-10)
    expect(await handler["internalCountTokens"]("hello2")).toBe(0)
  
    // 3) CancellationError thrown by client.countTokens
    mockLanguageModelChat.countTokens.mockRejectedValueOnce(new vscode.CancellationError())
    expect(await handler["internalCountTokens"]("should-cancel")).toBe(0)
  
    // 4) Generic error thrown (with stack) - should be caught and return 0
    const genericErr = new Error("boom")
    genericErr.stack = "stacktrace"
    mockLanguageModelChat.countTokens.mockRejectedValueOnce(genericErr)
    expect(await handler["internalCountTokens"]("will-error")).toBe(0)
  
    // 5) Empty chat message content should return 0 without calling countTokens
    const emptyChatMsg = vscode.LanguageModelChatMessage.Assistant([])
    expect(await handler["internalCountTokens"](emptyChatMsg)).toBe(0)
  })


  it("fallback client sendRequest produces text and countTokens returns 0", async () => {
    ;(vscode.lm.selectChatModels as Mock).mockResolvedValueOnce([])
  
    const client = await handler["createClient"]({})
    expect(client).toBeDefined()
    expect(client.id).toBe("default-lm")
  
    // call the fallback client's sendRequest and consume the stream
    const response = await client.sendRequest([], {}, new vscode.CancellationTokenSource().token)
    const parts: any[] = []
    for await (const p of response.stream) {
      parts.push(p)
    }
  
    expect(parts.length).toBeGreaterThanOrEqual(1)
    expect(parts[0]).toBeInstanceOf(vscode.LanguageModelTextPart)
    expect(parts[0].value).toContain("Language model functionality is limited")
  
    // countTokens on the fallback client should return 0
    const tokenCount = await client.countTokens()
    expect(tokenCount).toBe(0)
  })


  it("getVsCodeLmModels filters static blacklist and returns empty on error", async () => {
    // Prepare a list that includes blacklisted models and allowed ones
    const models = [
      { id: "allowed-1", name: "Allowed 1", vendor: "v", family: "f", version: "v1", maxInputTokens: 1, sendRequest: vi.fn(), countTokens: vi.fn() },
      { id: "claude-3.7-sonnet", name: "Blacklisted", vendor: "v", family: "f", version: "v1", maxInputTokens: 1, sendRequest: vi.fn(), countTokens: vi.fn() },
      { id: "allowed-2", name: "Allowed 2", vendor: "v", family: "f", version: "v1", maxInputTokens: 1, sendRequest: vi.fn(), countTokens: vi.fn() },
    ]
  
    ;(vscode.lm.selectChatModels as Mock).mockResolvedValueOnce(models)
  
    const filtered = await (await import("../vscode-lm")).getVsCodeLmModels()
    // Ensure blacklist removed
    expect(filtered.map((m: any) => m.id)).toEqual(["allowed-1", "allowed-2"])
  
    // Now simulate an error from selectChatModels and ensure we get an empty array
    ;(vscode.lm.selectChatModels as Mock).mockRejectedValueOnce(new Error("select failed"))
    const emptyResult = await (await import("../vscode-lm")).getVsCodeLmModels()
    expect(emptyResult).toEqual([])
  })


  it("createMessage skips invalid text parts and handles tool call processing errors (circular input)", async () => {
    // Prepare client and attach to handler
    handler["client"] = mockLanguageModelChat
    // Ensure token counting returns 0 for simplicity
    mockLanguageModelChat.countTokens.mockResolvedValue(0)
  
    // Create a circular object that will cause JSON.stringify to throw
    const circ: any = {}
    circ.self = circ
  
    // Build the response stream:
    // 1) A LanguageModelTextPart with a non-string value (should be skipped)
    // 2) A tool call with circular input (JSON.stringify will throw inside processing -> caught and skipped)
    // 3) A valid tool call (should be yielded)
    const stream = (async function* () {
      yield new vscode.LanguageModelTextPart(123 as any) // invalid text part value
      yield new vscode.LanguageModelToolCallPart("call-circ", "circTool", circ) // will throw on stringify
      yield new vscode.LanguageModelToolCallPart("call-good", "goodTool", { x: 1 }) // valid
      return
    })()
  
    mockLanguageModelChat.sendRequest.mockResolvedValueOnce({
      stream,
      text: (async function* () {
        yield ""
        return
      })(),
    })
  
    // Provide metadata with tools to allow tool_call yields
    const tools = [
      {
        type: "function" as const,
        function: {
          name: "goodTool",
          description: "Good tool",
          parameters: { type: "object", properties: { x: { type: "number" } } },
        },
      },
      {
        type: "function" as const,
        function: {
          name: "circTool",
          description: "Circ tool",
          parameters: { type: "object" },
        },
      },
    ]
  
    const systemPrompt = "sys"
    const messages: any[] = [{ role: "user", content: "run" }]
  
    const chunks: any[] = []
    for await (const chunk of handler.createMessage(systemPrompt, messages, { tools })) {
      chunks.push(chunk)
    }
  
    // We expect only the valid tool_call chunk and then the usage chunk.
    expect(chunks.length).toBe(2)
    expect(chunks[0]).toEqual({
      type: "tool_call",
      id: "call-good",
      name: "goodTool",
      arguments: JSON.stringify({ x: 1 }),
    })
    expect(chunks[1]).toMatchObject({ type: "usage", inputTokens: expect.any(Number) })
  })


  it("cleanMessageContent recursively cleans nested structures", () => {
    // Prepare a complex nested structure containing strings, arrays, objects and numbers
    const input = {
      a: "hello",
      b: ["one", { nested: "two", deep: [{ d: "three" }] }],
      c: 123,
      d: null,
    }
  
    // Use the handler instance created in beforeEach
    const cleaned = handler["cleanMessageContent"](input)
  
    // Expect the structure to be preserved but strings to remain strings and numbers unchanged
    expect(cleaned).toEqual({
      a: "hello",
      b: ["one", { nested: "two", deep: [{ d: "three" }] }],
      c: 123,
      d: null,
    })
  })

})
