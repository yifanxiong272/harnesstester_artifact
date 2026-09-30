// npx vitest run api/providers/__tests__/qwen-code-native-tools.spec.ts

// Mock filesystem - must come before other imports
vi.mock("node:fs", () => ({
	promises: {
		readFile: vi.fn(),
		writeFile: vi.fn(),
	},
}))

const mockCreate = vi.fn()
vi.mock("openai", () => {
	return {
		__esModule: true,
		default: vi.fn().mockImplementation(() => ({
			apiKey: "test-key",
			baseURL: "https://dashscope.aliyuncs.com/compatible-mode/v1",
			chat: {
				completions: {
					create: mockCreate,
				},
			},
		})),
	}
})

import { promises as fs } from "node:fs"
import { QwenCodeHandler } from "../qwen-code"
import { NativeToolCallParser } from "../../../core/assistant-message/NativeToolCallParser"
import type { ApiHandlerOptions } from "../../../shared/api"
import * as os from "os"
import * as path from "path"

describe("QwenCodeHandler Native Tools", () => {
	let handler: QwenCodeHandler
	let mockOptions: ApiHandlerOptions & { qwenCodeOauthPath?: string }

	const testTools = [
		{
			type: "function" as const,
			function: {
				name: "test_tool",
				description: "A test tool",
				parameters: {
					type: "object",
					properties: {
						arg1: { type: "string", description: "First argument" },
					},
					required: ["arg1"],
				},
			},
		},
	]

	beforeEach(() => {
		vi.clearAllMocks()

		// Mock credentials file
		const mockCredentials = {
			access_token: "test-access-token",
			refresh_token: "test-refresh-token",
			token_type: "Bearer",
			expiry_date: Date.now() + 3600000, // 1 hour from now
			resource_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
		}
		;(fs.readFile as any).mockResolvedValue(JSON.stringify(mockCredentials))
		;(fs.writeFile as any).mockResolvedValue(undefined)

		mockOptions = {
			apiModelId: "qwen3-coder-plus",
		}
		handler = new QwenCodeHandler(mockOptions)

		// Clear NativeToolCallParser state before each test
		NativeToolCallParser.clearRawChunkState()
	})

	describe("Native Tool Calling Support", () => {
		it("should include tools in request when model supports native tools and tools are provided", async () => {
			mockCreate.mockImplementationOnce(() => ({
				[Symbol.asyncIterator]: async function* () {
					yield {
						choices: [{ delta: { content: "Test response" } }],
					}
				},
			}))

			const stream = handler.createMessage("test prompt", [], {
				taskId: "test-task-id",
				tools: testTools,
			})
			await stream.next()

			expect(mockCreate).toHaveBeenCalledWith(
				expect.objectContaining({
					tools: expect.arrayContaining([
						expect.objectContaining({
							type: "function",
							function: expect.objectContaining({
								name: "test_tool",
							}),
						}),
					]),
					parallel_tool_calls: true,
				}),
			)
		})

		it("should include tool_choice when provided", async () => {
			mockCreate.mockImplementationOnce(() => ({
				[Symbol.asyncIterator]: async function* () {
					yield {
						choices: [{ delta: { content: "Test response" } }],
					}
				},
			}))

			const stream = handler.createMessage("test prompt", [], {
				taskId: "test-task-id",
				tools: testTools,
				tool_choice: "auto",
			})
			await stream.next()

			expect(mockCreate).toHaveBeenCalledWith(
				expect.objectContaining({
					tool_choice: "auto",
				}),
			)
		})

		it("should always include tools and tool_choice (tools are guaranteed to be present after ALWAYS_AVAILABLE_TOOLS)", async () => {
			mockCreate.mockImplementationOnce(() => ({
				[Symbol.asyncIterator]: async function* () {
					yield {
						choices: [{ delta: { content: "Test response" } }],
					}
				},
			}))

			const stream = handler.createMessage("test prompt", [], {
				taskId: "test-task-id",
			})
			await stream.next()

			// Tools are now always present (minimum 6 from ALWAYS_AVAILABLE_TOOLS)
			const callArgs = mockCreate.mock.calls[mockCreate.mock.calls.length - 1][0]
			expect(callArgs).toHaveProperty("tools")
			expect(callArgs).toHaveProperty("tool_choice")
			expect(callArgs).toHaveProperty("parallel_tool_calls", true)
		})

		it("should yield tool_call_partial chunks during streaming", async () => {
			mockCreate.mockImplementationOnce(() => ({
				[Symbol.asyncIterator]: async function* () {
					yield {
						choices: [
							{
								delta: {
									tool_calls: [
										{
											index: 0,
											id: "call_qwen_123",
											function: {
												name: "test_tool",
												arguments: '{"arg1":',
											},
										},
									],
								},
							},
						],
					}
					yield {
						choices: [
							{
								delta: {
									tool_calls: [
										{
											index: 0,
											function: {
												arguments: '"value"}',
											},
										},
									],
								},
							},
						],
					}
				},
			}))

			const stream = handler.createMessage("test prompt", [], {
				taskId: "test-task-id",
				tools: testTools,
			})

			const chunks = []
			for await (const chunk of stream) {
				chunks.push(chunk)
			}

			expect(chunks).toContainEqual({
				type: "tool_call_partial",
				index: 0,
				id: "call_qwen_123",
				name: "test_tool",
				arguments: '{"arg1":',
			})

			expect(chunks).toContainEqual({
				type: "tool_call_partial",
				index: 0,
				id: undefined,
				name: undefined,
				arguments: '"value"}',
			})
		})

		it("should set parallel_tool_calls based on metadata", async () => {
			mockCreate.mockImplementationOnce(() => ({
				[Symbol.asyncIterator]: async function* () {
					yield {
						choices: [{ delta: { content: "Test response" } }],
					}
				},
			}))

			const stream = handler.createMessage("test prompt", [], {
				taskId: "test-task-id",
				tools: testTools,
				parallelToolCalls: true,
			})
			await stream.next()

			expect(mockCreate).toHaveBeenCalledWith(
				expect.objectContaining({
					parallel_tool_calls: true,
				}),
			)
		})

		it("should yield tool_call_end events when finish_reason is tool_calls", async () => {
			mockCreate.mockImplementationOnce(() => ({
				[Symbol.asyncIterator]: async function* () {
					yield {
						choices: [
							{
								delta: {
									tool_calls: [
										{
											index: 0,
											id: "call_qwen_test",
											function: {
												name: "test_tool",
												arguments: '{"arg1":"value"}',
											},
										},
									],
								},
							},
						],
					}
					yield {
						choices: [
							{
								delta: {},
								finish_reason: "tool_calls",
							},
						],
						usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
					}
				},
			}))

			const stream = handler.createMessage("test prompt", [], {
				taskId: "test-task-id",
				tools: testTools,
			})

			const chunks = []
			for await (const chunk of stream) {
				// Simulate what Task.ts does: when we receive tool_call_partial,
				// process it through NativeToolCallParser to populate rawChunkTracker
				if (chunk.type === "tool_call_partial") {
					NativeToolCallParser.processRawChunk({
						index: chunk.index,
						id: chunk.id,
						name: chunk.name,
						arguments: chunk.arguments,
					})
				}
				chunks.push(chunk)
			}

			// Should have tool_call_partial and tool_call_end
			const partialChunks = chunks.filter((chunk) => chunk.type === "tool_call_partial")
			const endChunks = chunks.filter((chunk) => chunk.type === "tool_call_end")

			expect(partialChunks).toHaveLength(1)
			expect(endChunks).toHaveLength(1)
			expect(endChunks[0].id).toBe("call_qwen_test")
		})

		it("should preserve thinking block handling alongside tool calls", async () => {
			mockCreate.mockImplementationOnce(() => ({
				[Symbol.asyncIterator]: async function* () {
					yield {
						choices: [
							{
								delta: {
									reasoning_content: "Thinking about this...",
								},
							},
						],
					}
					yield {
						choices: [
							{
								delta: {
									tool_calls: [
										{
											index: 0,
											id: "call_after_think",
											function: {
												name: "test_tool",
												arguments: '{"arg1":"result"}',
											},
										},
									],
								},
							},
						],
					}
					yield {
						choices: [
							{
								delta: {},
								finish_reason: "tool_calls",
							},
						],
					}
				},
			}))

			const stream = handler.createMessage("test prompt", [], {
				taskId: "test-task-id",
				tools: testTools,
			})

			const chunks = []
			for await (const chunk of stream) {
				if (chunk.type === "tool_call_partial") {
					NativeToolCallParser.processRawChunk({
						index: chunk.index,
						id: chunk.id,
						name: chunk.name,
						arguments: chunk.arguments,
					})
				}
				chunks.push(chunk)
			}

			// Should have reasoning, tool_call_partial, and tool_call_end
			const reasoningChunks = chunks.filter((chunk) => chunk.type === "reasoning")
			const partialChunks = chunks.filter((chunk) => chunk.type === "tool_call_partial")
			const endChunks = chunks.filter((chunk) => chunk.type === "tool_call_end")

			expect(reasoningChunks).toHaveLength(1)
			expect(reasoningChunks[0].text).toBe("Thinking about this...")
			expect(partialChunks).toHaveLength(1)
			expect(endChunks).toHaveLength(1)
		})

  it("completePrompt rethrows non-401 errors from the API", async () => {
    vi.clearAllMocks()
  
    const creds = {
      access_token: "x",
      refresh_token: "r",
      token_type: "Bearer",
      expiry_date: Date.now() + 3600000,
      resource_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    ;(fs.readFile as any).mockResolvedValue(JSON.stringify(creds))
    ;(fs.writeFile as any).mockResolvedValue(undefined)
  
    // Simulate a 500 error from the API
    const apiError = { status: 500, message: "boom" }
    mockCreate.mockImplementationOnce(() => {
      throw apiError
    })
  
    const handler = new QwenCodeHandler({ apiModelId: "qwen3-coder-plus" })
    await expect(handler.completePrompt("test")).rejects.toMatchObject({ status: 500 })
  })


  it("completePrompt refreshes on 401 and retries successfully", async () => {
    vi.clearAllMocks()
  
    // Start with a valid (non-expired) cached credential so ensureAuthenticated doesn't pre-refresh
    const initialCreds = {
      access_token: "initial-token",
      refresh_token: "initial-refresh",
      token_type: "Bearer",
      expiry_date: Date.now() + 3600000,
      resource_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    ;(fs.readFile as any).mockResolvedValue(JSON.stringify(initialCreds))
    ;(fs.writeFile as any).mockResolvedValue(undefined)
  
    // Stub global.fetch to simulate token refresh endpoint returning a new token
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        access_token: "new-access-token",
        token_type: "Bearer",
        refresh_token: "new-refresh-token",
        expires_in: 3600,
      }),
    })
    // @ts-ignore - attach to global
    global.fetch = fetchMock
  
    // First API call throws 401, second call succeeds
    mockCreate
      .mockImplementationOnce(() => {
        throw { status: 401, message: "unauthorized" }
      })
      .mockImplementationOnce(() => {
        return {
          choices: [
            {
              message: { content: "final content" },
            },
          ],
        }
      })
  
    const handler = new QwenCodeHandler({ apiModelId: "qwen3-coder-plus" })
    const result = await handler.completePrompt("hello")
  
    expect(result).toBe("final content")
    // The client's apiKey should have been updated to the new access token
    expect((handler as any).client.apiKey).toBe("new-access-token")
    // Ensure fetch (token endpoint) was called
    expect(fetchMock).toHaveBeenCalled()
  
    // cleanup global.fetch to avoid affecting other tests
    // @ts-ignore
    delete global.fetch
  })


  it("refreshAccessToken throws and clears refreshPromise when no refresh_token present", async () => {
    vi.clearAllMocks()
    const handler = new QwenCodeHandler({ apiModelId: "qwen3-coder-plus" })
  
    // Credentials without refresh_token
    const badCreds = {
      access_token: "a",
      token_type: "Bearer",
      expiry_date: Date.now() + 10000,
    }
  
    // Also verify isTokenValid behavior for missing expiry_date
    const noExpiry = { access_token: "a" }
    expect((handler as any).isTokenValid(noExpiry)).toBe(false)
  
    // Call refreshAccessToken and assert it rejects with the expected message
    await expect((handler as any).refreshAccessToken(badCreds)).rejects.toThrow(
      "No refresh token available in credentials.",
    )
  
    // After failure, refreshPromise should be cleared (null)
    expect((handler as any).refreshPromise).toBeNull()
  })


  it("loadCachedQwenCredentials errors are propagated to createMessage", async () => {
    vi.clearAllMocks()
    // Make readFile fail
    ;(fs.readFile as any).mockRejectedValue(new Error("no file"))
  
    const handler = new QwenCodeHandler({ apiModelId: "qwen3-coder-plus" })
    const stream = handler.createMessage("prompt", [], { taskId: "t" })
  
    await expect(stream.next()).rejects.toThrow("Failed to load Qwen OAuth credentials")
  })


  it("should throw when token endpoint returns error payload in JSON", async () => {
    // Arrange: stub global.fetch to return ok:true but json contains error keys
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ error: "invalid_grant", error_description: "Refresh token invalid" }),
    })
    vi.stubGlobal("fetch", fetchMock)
  
    const creds = {
      access_token: "a",
      refresh_token: "r",
      token_type: "Bearer",
      expiry_date: Date.now() - 1000,
    }
  
    await expect((handler as any).doRefreshAccessToken(creds)).rejects.toThrow(
      "Token refresh failed: invalid_grant - Refresh token invalid",
    )
  
    // Cleanup stub
    vi.unstubAllGlobals()
  })


  it("should throw when token endpoint returns non-ok response", async () => {
    // Arrange: stub global.fetch to return a non-ok response
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: "Forbidden",
      text: async () => "bad response body",
    })
    vi.stubGlobal("fetch", fetchMock)
  
    const creds = {
      access_token: "a",
      refresh_token: "r",
      token_type: "Bearer",
      expiry_date: Date.now() - 1000,
    }
  
    // Act & Assert
    await expect((handler as any).doRefreshAccessToken(creds)).rejects.toThrow(
      "Token refresh failed: 403 Forbidden. Response: bad response body",
    )
  
    // Cleanup stub
    vi.unstubAllGlobals()
  })


  it("should refresh credentials on 401 and retry the apiCall", async () => {
    // Arrange: put initial credentials on the handler
    const initialCreds = {
      access_token: "old-token",
      refresh_token: "old-refresh",
      token_type: "Bearer",
      expiry_date: Date.now() + 10000,
      resource_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    ;(handler as any).credentials = initialCreds
  
    // apiCall fails first time with status 401, then succeeds
    let callCount = 0
    const apiCall = vi.fn().mockImplementation(() => {
      callCount++
      if (callCount === 1) {
        const err: any = new Error("unauthorized")
        err.status = 401
        return Promise.reject(err)
      }
      return Promise.resolve("success-result")
    })
  
    // Spy on refreshAccessToken to return new credentials
    const newCreds = {
      access_token: "new-token",
      refresh_token: "new-refresh",
      token_type: "Bearer",
      expiry_date: Date.now() + 3600000,
      resource_url: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    }
    const refreshSpy = vi.spyOn(handler as any, "refreshAccessToken").mockResolvedValue(newCreds)
  
    // Ensure client exists so callApiWithRetry can set apiKey/baseURL after refresh
    ;(handler as any).client = undefined
    // Act
    const result = await (handler as any).callApiWithRetry(apiCall)
  
    // Assert: apiCall retried and returned result; refreshAccessToken was invoked
    expect(apiCall).toHaveBeenCalledTimes(2)
    expect(refreshSpy).toHaveBeenCalled()
    expect(result).toBe("success-result")
    // The handler's client should have been updated with the new access token
    expect((handler as any).client.apiKey).toBe(newCreds.access_token)
  })


  it("should parse <think> blocks and handle repeated prefix content correctly", async () => {
    // Arrange: Prepare stream that first sends "Hello" then sends "Hello<think>mid</think>End"
    mockCreate.mockImplementationOnce(() => ({
      [Symbol.asyncIterator]: async function* () {
        yield {
          choices: [{ delta: { content: "Hello" } }],
        }
        yield {
          choices: [{ delta: { content: "Hello<think>mid</think>End" } }],
        }
      },
    }))
  
    const stream = handler.createMessage("test prompt", [], {
      taskId: "test-task-id",
    })
  
    const chunks: any[] = []
    for await (const chunk of stream) {
      chunks.push(chunk)
    }
  
    // Expect sequence:
    // 1) text "Hello"
    // 2) reasoning "mid" (from <think> block)
    // 3) text "End"
    expect(chunks).toContainEqual({ type: "text", text: "Hello" })
    expect(chunks).toContainEqual({ type: "reasoning", text: "mid" })
    expect(chunks).toContainEqual({ type: "text", text: "End" })
  })


  it("doRefreshAccessToken should POST urlencoded data and handle writeFile failure and return updated credentials", async () => {
    vi.clearAllMocks()
    const handler = new QwenCodeHandler({ qwenCodeOauthPath: "/tmp/creds.json" })
  
    const initialCreds = {
      access_token: "old",
      refresh_token: "ref-token",
      token_type: "Bearer",
      expiry_date: Date.now() - 100000, // expired to simulate refresh scenario
      resource_url: "example.com",
    }
  
    // Mock fetch to return a successful token response
    const mockFetchResponse = {
      ok: true,
      json: async () => ({
        access_token: "new-access",
        token_type: "Bearer",
        refresh_token: "new-refresh",
        expires_in: 3600,
      }),
    }
    // Capture the fetch call for assertions
    ;(global as any).fetch = vi.fn().mockResolvedValue(mockFetchResponse)
  
    // Simulate writeFile failing (should be caught and not re-thrown)
    ;(fs.writeFile as any).mockRejectedValue(new Error("disk full"))
  
    const result = await (handler as any).doRefreshAccessToken(initialCreds)
  
    // Ensure new token values are present
    expect(result.access_token).toBe("new-access")
    expect(result.refresh_token).toBe("new-refresh")
    expect(typeof result.expiry_date).toBe("number")
  
    // Verify fetch was called to the QWEN token endpoint with POST and urlencoded body
    expect((global as any).fetch).toHaveBeenCalled()
    const fetchCall = (global as any).fetch.mock.calls[0]
    expect(fetchCall[0]).toContain("qwen.ai/api/v1/oauth2/token")
    const fetchOptions = fetchCall[1]
    expect(fetchOptions.method).toBe("POST")
    expect(fetchOptions.headers["Content-Type"]).toBe("application/x-www-form-urlencoded")
  
    // Body should be urlencoded and include the refresh_token and client_id
    const body = fetchOptions.body as string
    expect(body).toContain("refresh_token=" + encodeURIComponent("ref-token"))
    expect(body).toContain("client_id=f0304373b74a44d2b584a3fb70ca9e56")
  
    // writeFile should have been attempted despite failing
    expect(fs.writeFile).toHaveBeenCalled()
  
    // getBaseUrl should add https:// and /v1 for a resource_url without scheme
    const base = (handler as any).getBaseUrl({ resource_url: "example.com" })
    expect(base).toBe("https://example.com/v1")
  })


  it("doRefreshAccessToken should throw when no refresh_token", async () => {
    vi.clearAllMocks()
    const handler = new QwenCodeHandler({})
  
    // Call private method directly (via any) with missing refresh_token
    await expect(
      (handler as any).doRefreshAccessToken({
        access_token: "a",
        // refresh_token omitted intentionally
        token_type: "Bearer",
        expiry_date: Date.now() + 10000,
      }),
    ).rejects.toThrow("No refresh token available in credentials.")
  })


  it("expands ~ and resolves absolute oauth path when loading credentials", async () => {
    vi.clearAllMocks()
    // Prepare mock credentials content
    const mockCredentials = {
      access_token: "test-access-token",
      refresh_token: "test-refresh-token",
      token_type: "Bearer",
      expiry_date: Date.now() + 3600000,
    }
    ;(fs.readFile as any).mockResolvedValue(JSON.stringify(mockCredentials))
  
    // Case 1: path starting with ~/
    const tildePath = "~/my/creds.json"
    const handlerTilde = new QwenCodeHandler({ qwenCodeOauthPath: tildePath })
    const loaded1 = await (handlerTilde as any).loadCachedQwenCredentials()
    expect(loaded1.access_token).toBe("test-access-token")
    // Expect readFile called with expanded home path
    expect(fs.readFile).toHaveBeenCalledWith(path.join(os.homedir(), "my/creds.json"), "utf-8")
  
    // Case 2: absolute path should be resolved as-is (path.resolve on absolute returns same)
    const absPath = "/tmp/other_creds.json"
    const handlerAbs = new QwenCodeHandler({ qwenCodeOauthPath: absPath })
    const loaded2 = await (handlerAbs as any).loadCachedQwenCredentials()
    expect(loaded2.access_token).toBe("test-access-token")
    expect(fs.readFile).toHaveBeenCalledWith(path.resolve(absPath), "utf-8")
  })

	})
})
