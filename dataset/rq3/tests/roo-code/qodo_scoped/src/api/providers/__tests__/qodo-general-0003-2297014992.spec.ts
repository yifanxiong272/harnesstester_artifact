// cd src && npx vitest run api/providers/__tests__/openai-codex-native-tool-calls.spec.ts

import { beforeEach, describe, expect, it, vi } from "vitest"

import { OpenAiCodexHandler } from "../openai-codex"
import type { ApiHandlerOptions } from "../../../shared/api"
import { NativeToolCallParser } from "../../../core/assistant-message/NativeToolCallParser"
import { openAiCodexOAuthManager } from "../../../integrations/openai-codex/oauth"

describe("OpenAiCodexHandler native tool calls", () => {
	let handler: OpenAiCodexHandler
	let mockOptions: ApiHandlerOptions

	beforeEach(() => {
		vi.restoreAllMocks()
		NativeToolCallParser.clearRawChunkState()
		NativeToolCallParser.clearAllStreamingToolCalls()

		mockOptions = {
			apiModelId: "gpt-5.2-2025-12-11",
			// minimal settings; OAuth is mocked below
		}
		handler = new OpenAiCodexHandler(mockOptions)
	})

	it("yields tool_call_partial chunks when API returns function_call-only response", async () => {
		vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("test-token")
		vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_test")

		// Mock OpenAI SDK streaming (preferred path).
		;(handler as any).client = {
			responses: {
				create: vi.fn().mockResolvedValue({
					async *[Symbol.asyncIterator]() {
						yield {
							type: "response.output_item.added",
							item: {
								type: "function_call",
								call_id: "call_1",
								name: "attempt_completion",
								arguments: "",
							},
							output_index: 0,
						}
						yield {
							type: "response.function_call_arguments.delta",
							delta: '{"result":"hi"}',
							// Note: intentionally omit call_id + name to simulate tool-call-only streams.
							item_id: "fc_1",
							output_index: 0,
						}
						yield {
							type: "response.completed",
							response: {
								id: "resp_1",
								status: "completed",
								output: [
									{
										type: "function_call",
										call_id: "call_1",
										name: "attempt_completion",
										arguments: '{"result":"hi"}',
									},
								],
								usage: { input_tokens: 1, output_tokens: 1 },
							},
						}
					},
				}),
			},
		}

		const stream = handler.createMessage("system", [{ role: "user", content: "hello" } as any], {
			taskId: "t",
			tools: [],
		})

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
			if (chunk.type === "tool_call_partial") {
				// Simulate Task.ts behavior so finish_reason handling can emit tool_call_end elsewhere
				NativeToolCallParser.processRawChunk({
					index: chunk.index,
					id: chunk.id,
					name: chunk.name,
					arguments: chunk.arguments,
				})
			}
		}

		const toolChunks = chunks.filter((c) => c.type === "tool_call_partial")
		expect(toolChunks.length).toBeGreaterThan(0)
		expect(toolChunks[0]).toMatchObject({
			type: "tool_call_partial",
			id: "call_1",
			name: "attempt_completion",
		})
	})

	it("yields text when Codex emits assistant message only in response.output_item.done", async () => {
		vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("test-token")
		vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_test")
		;(handler as any).client = {
			responses: {
				create: vi.fn().mockResolvedValue({
					async *[Symbol.asyncIterator]() {
						yield {
							type: "response.output_item.done",
							item: {
								type: "message",
								role: "assistant",
								content: [{ type: "output_text", text: "hello from spark" }],
							},
							output_index: 0,
						}
						yield {
							type: "response.completed",
							response: {
								id: "resp_done_only",
								status: "completed",
								output: [
									{
										type: "message",
										role: "assistant",
										content: [{ type: "output_text", text: "hello from spark" }],
									},
								],
								usage: { input_tokens: 1, output_tokens: 2 },
							},
						}
					},
				}),
			},
		}

		const stream = handler.createMessage("system", [{ role: "user", content: "test" } as any], {
			taskId: "t",
			tools: [],
		})

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
		}

		const textChunks = chunks.filter((c) => c.type === "text")
		expect(textChunks.length).toBeGreaterThan(0)
		expect(textChunks.map((c) => c.text).join("")).toContain("hello from spark")
	})

	it("yields text when Codex emits assistant message only in response.completed output", async () => {
		vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("test-token")
		vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_test")
		;(handler as any).client = {
			responses: {
				create: vi.fn().mockResolvedValue({
					async *[Symbol.asyncIterator]() {
						yield {
							type: "response.completed",
							response: {
								id: "resp_completed_only",
								status: "completed",
								output: [
									{
										type: "message",
										role: "assistant",
										content: [{ type: "output_text", text: "final payload only" }],
									},
								],
								usage: { input_tokens: 1, output_tokens: 2 },
							},
						}
					},
				}),
			},
		}

		const stream = handler.createMessage("system", [{ role: "user", content: "test" } as any], {
			taskId: "t",
			tools: [],
		})

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
		}

		const textChunks = chunks.filter((c) => c.type === "text")
		expect(textChunks.length).toBeGreaterThan(0)
		expect(textChunks.map((c) => c.text).join("")).toContain("final payload only")
	})

	it("yields text when Codex emits response.output_text.done without deltas", async () => {
		vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("test-token")
		vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_test")
		;(handler as any).client = {
			responses: {
				create: vi.fn().mockResolvedValue({
					async *[Symbol.asyncIterator]() {
						yield {
							type: "response.output_text.done",
							text: "done-event text only",
						}
						yield {
							type: "response.completed",
							response: {
								id: "resp_done_text_only",
								status: "completed",
								output: [],
								usage: { input_tokens: 1, output_tokens: 2 },
							},
						}
					},
				}),
			},
		}

		const stream = handler.createMessage("system", [{ role: "user", content: "test" } as any], {
			taskId: "t",
			tools: [],
		})

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
		}

		const textChunks = chunks.filter((c) => c.type === "text")
		expect(textChunks.length).toBeGreaterThan(0)
		expect(textChunks.map((c) => c.text).join("")).toContain("done-event text only")
	})

	it("yields tool_call when Codex emits function_call only in response.output_item.done", async () => {
		vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("test-token")
		vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_test")
		;(handler as any).client = {
			responses: {
				create: vi.fn().mockResolvedValue({
					async *[Symbol.asyncIterator]() {
						yield {
							type: "response.output_item.done",
							item: {
								type: "function_call",
								call_id: "call_done_only",
								name: "attempt_completion",
								arguments: '{"result":"ok"}',
							},
							output_index: 0,
						}
						yield {
							type: "response.completed",
							response: {
								id: "resp_done_tool_only",
								status: "completed",
								output: [],
								usage: { input_tokens: 1, output_tokens: 2 },
							},
						}
					},
				}),
			},
		}

		const stream = handler.createMessage("system", [{ role: "user", content: "test" } as any], {
			taskId: "t",
			tools: [],
		})

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
		}

		const toolCalls = chunks.filter((c) => c.type === "tool_call")
		expect(toolCalls.length).toBeGreaterThan(0)
		expect(toolCalls[0]).toMatchObject({
			type: "tool_call",
			id: "call_done_only",
			name: "attempt_completion",
		})
	})

	it("yields text when Codex emits response.content_part.added", async () => {
		vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("test-token")
		vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_test")
		;(handler as any).client = {
			responses: {
				create: vi.fn().mockResolvedValue({
					async *[Symbol.asyncIterator]() {
						yield {
							type: "response.content_part.added",
							part: {
								type: "output_text",
								text: "content part text",
							},
							output_index: 0,
							content_index: 0,
						}
						yield {
							type: "response.completed",
							response: {
								id: "resp_content_part",
								status: "completed",
								output: [],
								usage: { input_tokens: 1, output_tokens: 2 },
							},
						}
					},
				}),
			},
		}

		const stream = handler.createMessage("system", [{ role: "user", content: "test" } as any], {
			taskId: "t",
			tools: [],
		})

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
		}

		const textChunks = chunks.filter((c) => c.type === "text")
		expect(textChunks.length).toBeGreaterThan(0)
		expect(textChunks.map((c) => c.text).join("")).toContain("content part text")
	})

	it("does not duplicate text when Codex emits delta and output_text.done", async () => {
		vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("test-token")
		vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_test")
		;(handler as any).client = {
			responses: {
				create: vi.fn().mockResolvedValue({
					async *[Symbol.asyncIterator]() {
						yield { type: "response.output_text.delta", delta: "hello " }
						yield { type: "response.output_text.delta", delta: "world" }
						yield { type: "response.output_text.done", text: "hello world" }
						yield {
							type: "response.completed",
							response: {
								id: "resp_delta_done",
								status: "completed",
								output: [],
								usage: { input_tokens: 1, output_tokens: 2 },
							},
						}
					},
				}),
			},
		}

		const stream = handler.createMessage("system", [{ role: "user", content: "test" } as any], {
			taskId: "t",
			tools: [],
		})

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
		}

		const textChunks = chunks.filter((c) => c.type === "text")
		expect(textChunks.map((c) => c.text).join("")).toBe("hello world")
	})

	it("does not duplicate text when Codex emits delta and content_part.added", async () => {
		vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("test-token")
		vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_test")
		;(handler as any).client = {
			responses: {
				create: vi.fn().mockResolvedValue({
					async *[Symbol.asyncIterator]() {
						yield { type: "response.output_text.delta", delta: "hello world" }
						yield {
							type: "response.content_part.added",
							part: { type: "output_text", text: "hello world" },
							output_index: 0,
							content_index: 0,
						}
						yield {
							type: "response.completed",
							response: {
								id: "resp_delta_content_part",
								status: "completed",
								output: [],
								usage: { input_tokens: 1, output_tokens: 2 },
							},
						}
					},
				}),
			},
		}

		const stream = handler.createMessage("system", [{ role: "user", content: "test" } as any], {
			taskId: "t",
			tools: [],
		})

		const chunks: any[] = []
		for await (const chunk of stream) {
			chunks.push(chunk)
		}

		const textChunks = chunks.filter((c) => c.type === "text")
		expect(textChunks.map((c) => c.text).join("")).toBe("hello world")
	})

 it("completePrompt sends reasoning when configured and returns response.text", async () => {
   vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("token_complete")
   vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue(null)
   // Enable reasoning on the handler options
   handler.options.reasoningEffort = "high"
   // Mock global.fetch to capture the request and return a simple { text }
   const fetchMock = vi.fn().mockResolvedValue({
     ok: true,
     json: async () => ({ text: "the-response-text" }),
   })
   ;(global as any).fetch = fetchMock
   try {
     const result = await handler.completePrompt("a quick prompt")
     expect(result).toBe("the-response-text")
     expect(fetchMock).toHaveBeenCalled()
     const fetchCall = fetchMock.mock.calls[0]
     // The second argument should be the init object
     const init = fetchCall[1]
     expect(init).toBeDefined()
     const sentBody = JSON.parse(init.body)
     // When reasoning is enabled, include should contain reasoning.encrypted_content
     expect(sentBody.include).toEqual(["reasoning.encrypted_content"])
     // And reasoning.effort should match the handler option
     expect(sentBody.reasoning).toBeDefined()
     expect(sentBody.reasoning.effort).toBe("high")
   } finally {
     // Clean up fetch mock so other tests are unaffected
     ;(global as any).fetch = undefined
   }
 })


 it("completePrompt returns message text from response output", async () => {
   vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("tok")
   vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_1")
 
   // Stub global fetch to simulate successful /responses POST returning an output message.
   vi.stubGlobal(
     "fetch",
     vi.fn().mockResolvedValue({
       ok: true,
       json: async () => ({
         output: [
           {
             type: "message",
             content: [{ type: "output_text", text: "the result" }],
           },
         ],
       }),
     }),
   )
 
   const result = await handler.completePrompt("some prompt")
   expect(result).toBe("the result")
 })


 it("retries with forceRefreshAccessToken on auth failure and succeeds", async () => {
   // initial token returned, then force refresh provides a refreshed token
   vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("initial-token")
   const forceSpy = vi
     .spyOn(openAiCodexOAuthManager, "forceRefreshAccessToken")
     .mockResolvedValue("refreshed-token")
 
   // Mock handler.executeRequest to throw on the initial token, and to return a small async generator for the refreshed token.
   vi.spyOn(handler as any, "executeRequest").mockImplementation(
     (requestBody: any, model: any, accessToken: string) => {
       if (accessToken === "initial-token") {
         throw new Error("401 Unauthorized")
       }
       // Return an async generator that yields one text chunk
       return (async function* () {
         yield { type: "text", text: "after-refresh" }
       })()
     },
   )
 
   const chunks: any[] = []
   for await (const chunk of handler.createMessage("system", [{ role: "user", content: "x" } as any])) {
     chunks.push(chunk)
   }
 
   expect(forceSpy).toHaveBeenCalled()
   expect(chunks.some((c) => c.type === "text" && c.text === "after-refresh")).toBe(true)
 })


 it("throws when not authenticated for createMessage", async () => {
   // Simulate not authenticated
   vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue(null)
 
   const gen = handler.createMessage("system", [{ role: "user", content: "hi" } as any])
   // The async generator will throw when first advanced
   await expect(gen.next()).rejects.toThrow(/Not authenticated with OpenAI Codex/i)
 })


 it("completePrompt sends reasoning fields and returns message text", async () => {
   vi.restoreAllMocks()
   // Ensure handler options include a reasoning effort to trigger include + reasoning
   handler.options.reasoningEffort = "average"
 
   vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("comp-token")
   vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue(undefined)
 
   // Capture the body passed to fetch and respond with valid message output
   let capturedBody = ""
   vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
     ok: true,
     json: async () => ({
       output: [
         {
           type: "message",
           content: [{ type: "output_text", text: "completion result here" }],
         },
       ],
     }),
     // completePrompt also may call text() during errors; provide it regardless
     text: async () => capturedBody,
     body: null,
   }))
 
   const res = await handler.completePrompt("Make this short")
   expect(res).toBe("completion result here")
 
   // Inspect the last fetch invocation to assert reasoning fields were sent.
   // Vitest's stub gives us the mock function so read its last call.
   const mockFetch = (fetch as unknown) as ReturnType<typeof vi.fn>
   const lastCall = (mockFetch as any).mock.calls.slice(-1)[0]
   expect(lastCall).toBeDefined()
   const fetchOptions = lastCall[1]
   expect(fetchOptions.method).toBe("POST")
   capturedBody = fetchOptions.body
   expect(typeof capturedBody).toBe("string")
   const parsed = JSON.parse(capturedBody)
   // Should include the include array when reasoning is enabled
   expect(parsed.include).toEqual(["reasoning.encrypted_content"])
   // Should include a reasoning object with effort 'average' and summary 'auto'
   expect(parsed.reasoning).toBeDefined()
   expect(parsed.reasoning.effort).toBe("average")
   expect(parsed.reasoning.summary).toBe("auto")
 })


 it("yields usage and encrypted content via SSE fallback", async () => {
   vi.restoreAllMocks()
   NativeToolCallParser.clearRawChunkState()
   NativeToolCallParser.clearAllStreamingToolCalls()
 
   // Force SDK to be undefined so executeRequest falls back to makeCodexRequest (fetch)
   ;(handler as any).client = undefined
 
   // OAuth mocks
   vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("sse-token")
   vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_sse")
 
   // Prepare SSE-like lines. Intentionally omit top-level input_tokens to exercise
   // the input_tokens_details cached/cache_miss summation fallback.
   const payload = {
     response: {
       id: "resp_sse_1",
       output: [
         {
           type: "reasoning",
           encrypted_content: "enc_payload_123",
           id: "reasoning_1",
         },
       ],
       usage: {
         // No input_tokens field; use details to compute total input tokens
         input_tokens_details: {
           cached_tokens: 2,
           cache_miss_tokens: 3,
         },
         // output tokens normal place
         output_tokens: 5,
         // cache write/read various alternative fields
         cache_creation_input_tokens: 7,
         cache_read_input_tokens: 4,
         output_tokens_details: {
           reasoning_tokens: 9,
         },
       },
     },
   }
 
   const encoder = new TextEncoder()
   const sseLine = `data: ${JSON.stringify(payload)}\n`
   const doneLine = `data: [DONE]\n`
   const chunks = [encoder.encode(sseLine), encoder.encode(doneLine)]
 
   // Mock global fetch to return an object with body.getReader()
   vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
     ok: true,
     body: {
       getReader() {
         let i = 0
         return {
           async read() {
             if (i >= chunks.length) return { done: true, value: undefined }
             const v = chunks[i++]
             return { done: false, value: v }
           },
           releaseLock() {},
         }
       },
     },
   }))
 
   const stream = handler.createMessage("sys", [{ role: "user", content: "hi" } as any], {
     taskId: "task-sse",
     tools: [],
   })
 
   const out: any[] = []
   for await (const chunk of stream) {
     out.push(chunk)
   }
 
   // Find usage chunk
   const usageChunks = out.filter((c) => c.type === "usage")
   expect(usageChunks.length).toBeGreaterThan(0)
   const usage = usageChunks[0]
   // inputTokens should be cached + cache_miss = 5
   expect(usage.inputTokens).toBe(5)
   expect(usage.outputTokens).toBe(5)
   // cache write/read tokens presence
   expect(usage.cacheWriteTokens).toBe(7)
   expect(usage.cacheReadTokens).toBe(4)
   // reasoning tokens included
   expect(usage).toHaveProperty("reasoningTokens", 9)
   expect(usage.totalCost).toBe(0)
 
   // Verify encrypted content and response id are captured on handler
   const enc = handler.getEncryptedContent()
   expect(enc).toBeDefined()
   expect(enc?.encrypted_content).toBe("enc_payload_123")
   expect(enc?.id).toBe("reasoning_1")
 
   const rid = handler.getResponseId()
   expect(rid).toBe("resp_sse_1")
 })

})
