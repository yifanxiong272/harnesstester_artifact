// cd src && npx vitest run api/providers/__tests__/openai-codex-native-tool-calls.spec.ts

import { beforeEach, describe, expect, it, vi } from "vitest"

import { OpenAiCodexHandler } from "../openai-codex"
import type { ApiHandlerOptions } from "../../../shared/api"
import { NativeToolCallParser } from "../../../core/assistant-message/NativeToolCallParser"
import { openAiCodexOAuthManager } from "../../../integrations/openai-codex/oauth"
import * as mcpName from "../../../utils/mcp-name"

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

 it("processEvent sets lastResponseOutput/Id and getEncryptedContent/getResponseId/getReasoningEffort", async () => {
   const model = handler.getModel()
   const event = {
     response: {
       id: "respX",
       output: [
         {
           type: "reasoning",
           encrypted_content: "ENC",
           id: "reason1",
         },
       ],
     },
   }
   // processEvent is an async generator; iterate to allow processing side-effects
   for await (const _chunk of (handler as any).processEvent(event, model)) {
     // processEvent does not necessarily yield for this payload; just iterate
   }
   // getResponseId should reflect the last processed id
   expect((handler as any).getResponseId()).toBe("respX")
   // getEncryptedContent should return encrypted_content and id
   expect((handler as any).getEncryptedContent()).toEqual({ encrypted_content: "ENC", id: "reason1" })
   // Test reasoning effort selection behavior
   handler.options.reasoningEffort = "disable"
   expect((handler as any).getReasoningEffort(model)).toBeUndefined()
   handler.options.reasoningEffort = "deep"
   expect((handler as any).getReasoningEffort(model)).toBe("deep")
 })


 it("buildRequestBody uses ensureAdditionalPropertiesFalse for MCP tools", () => {
   // Spy on MCP detection to force MCP branch
   vi.spyOn(mcpName, "isMcpTool").mockReturnValue(true)
   const model = handler.getModel()
   const params = {
     type: "object",
     properties: {
       top: {
         type: "object",
         properties: {
           child: { type: "object", properties: { inner: { type: "string" } } },
         },
         additionalProperties: true,
       },
     },
     additionalProperties: true,
   }
   const metadata: any = {
     tools: [
       {
         type: "function",
         function: {
           name: "mcp_tool",
           description: "mcp",
           parameters: params,
         },
       },
     ],
   }
   const body = (handler as any).buildRequestBody(model, [], "sys", undefined, metadata)
   const tool = body.tools[0]
   // MCP -> strict false
   expect(tool.strict).toBe(false)
   const p = tool.parameters
   // ensureAdditionalPropertiesFalse forces additionalProperties=false, but does not inject required arrays
   expect(p.additionalProperties).toBe(false)
   expect(p.required).toBeUndefined()
   // Nested additionalProperties corrected as well
   expect(p.properties.top.additionalProperties).toBe(false)
   // restore spy for cleanliness
   vi.restoreAllMocks()
 })


 it("buildRequestBody sets required/additionalProperties for non-mcp tools", () => {
   // Prepare a model and nested tool parameter schema to exercise ensureAllRequired
   const model = handler.getModel()
   const params = {
     type: "object",
     properties: {
       top: {
         type: "object",
         properties: {
           child: {
             type: "object",
             properties: {
               inner: { type: "string" },
             },
           },
         },
       },
       arr: {
         type: "array",
         items: {
           type: "object",
           properties: {
             arrprop: { type: "string" },
           },
         },
       },
     },
   }
   const metadata: any = {
     tools: [
       {
         type: "function",
         function: {
           name: "normal_tool",
           description: "desc",
           parameters: params,
         },
       },
     ],
   }
   // Call private buildRequestBody
   const body = (handler as any).buildRequestBody(model, [], "sys", undefined, metadata)
   expect(body.tools).toBeDefined()
   const tool = body.tools[0]
   // non-mcp should be strict
   expect(tool.strict).toBe(true)
   const p = tool.parameters
   // Top-level additionalProperties should be false
   expect(p.additionalProperties).toBe(false)
   // Top-level required should include both properties 'top' and 'arr'
   expect(Array.isArray(p.required)).toBe(true)
   expect(p.required).toEqual(expect.arrayContaining(["top", "arr"]))
   // Nested required keys should be set for object children
   expect(p.properties.top.additionalProperties).toBe(false)
   expect(Array.isArray(p.properties.top.required)).toBe(true)
   expect(p.properties.top.required).toEqual(expect.arrayContaining(["child"]))
   // Inner-most required
   expect(p.properties.top.properties.child.required).toEqual(expect.arrayContaining(["inner"]))
   // Array items processed too: the items object should have required describing its properties
   expect(p.properties.arr.items.additionalProperties).toBe(false)
   expect(p.properties.arr.items.required).toEqual(expect.arrayContaining(["arrprop"]))
 })


 it("completePrompt returns output_text when present in response", async () => {
   vi.spyOn(openAiCodexOAuthManager, "getAccessToken").mockResolvedValue("token_x")
   vi.spyOn(openAiCodexOAuthManager, "getAccountId").mockResolvedValue("acct_123")
   // Stub global fetch to return a successful payload
   vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
     ok: true,
     json: async () => ({
       output: [
         {
           type: "message",
           content: [{ type: "output_text", text: "the answer" }],
         },
       ],
     }),
   }))
   const result = await handler.completePrompt("say hi")
   expect(result).toBe("the answer")
   // Cleanup fetch stub
   vi.stubGlobal("fetch", undefined)
 })


 it("normalizeUsage computes totals and includes reasoning tokens", () => {
   const model = handler.getModel()
   const usage = {
     input_tokens: 0,
     input_tokens_details: { cached_tokens: 2, cache_miss_tokens: 3 },
     output_tokens: 5,
     cache_creation_input_tokens: 1,
     cache_read_input_tokens: 4,
     output_tokens_details: { reasoning_tokens: 7 },
   }
   const out = (handler as any).normalizeUsage(usage, model)
   expect(out).toBeDefined()
   expect(out.type).toBe("usage")
   expect(out.inputTokens).toBe(5) // cached + miss
   expect(out.outputTokens).toBe(5)
   expect(out.cacheWriteTokens).toBe(1)
   expect(out.cacheReadTokens).toBe(4)
   // reasoning tokens included
   expect((out as any).reasoningTokens).toBe(7)
   expect(out.totalCost).toBe(0)
 })

})
