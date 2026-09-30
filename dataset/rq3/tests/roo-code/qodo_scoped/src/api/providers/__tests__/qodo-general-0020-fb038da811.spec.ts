import { t } from "i18next"
import { FunctionCallingConfigMode } from "@google/genai"

import { GeminiHandler } from "../gemini"
import type { ApiHandlerOptions } from "../../../shared/api"

describe("GeminiHandler backend support", () => {
	it("createMessage uses function declarations (URL context and grounding are only for completePrompt)", async () => {
		// URL context and grounding are mutually exclusive with function declarations
		// in Gemini API, so createMessage only uses function declarations.
		// URL context/grounding are only added in completePrompt.
		const options = {
			apiProvider: "gemini",
			enableUrlContext: true,
			enableGrounding: true,
		} as ApiHandlerOptions
		const handler = new GeminiHandler(options)
		const stub = vi.fn().mockReturnValue((async function* () {})())
		// @ts-ignore access private client
		handler["client"].models.generateContentStream = stub
		await handler.createMessage("instr", [] as any).next()
		const config = stub.mock.calls[0][0].config
		// createMessage always uses function declarations only
		// (tools are always present from ALWAYS_AVAILABLE_TOOLS)
		expect(config.tools).toEqual([{ functionDeclarations: expect.any(Array) }])
	})

	it("completePrompt passes config overrides without tools when URL context and grounding disabled", async () => {
		const options = {
			apiProvider: "gemini",
			enableUrlContext: false,
			enableGrounding: false,
		} as ApiHandlerOptions
		const handler = new GeminiHandler(options)
		const stub = vi.fn().mockResolvedValue({ text: "ok" })
		// @ts-ignore access private client
		handler["client"].models.generateContent = stub
		const res = await handler.completePrompt("hi")
		expect(res).toBe("ok")
		const promptConfig = stub.mock.calls[0][0].config
		expect(promptConfig.tools).toBeUndefined()
	})

	describe("error scenarios", () => {
		it("should handle grounding metadata extraction failure gracefully", async () => {
			const options = {
				apiProvider: "gemini",
				enableGrounding: true,
			} as ApiHandlerOptions
			const handler = new GeminiHandler(options)

			const mockStream = async function* () {
				yield {
					candidates: [
						{
							groundingMetadata: {
								// Invalid structure - missing groundingChunks
							},
							content: { parts: [{ text: "test response" }] },
						},
					],
					usageMetadata: { promptTokenCount: 10, candidatesTokenCount: 5 },
				}
			}

			const stub = vi.fn().mockReturnValue(mockStream())
			// @ts-ignore access private client
			handler["client"].models.generateContentStream = stub

			const messages = []
			for await (const chunk of handler.createMessage("test", [] as any)) {
				messages.push(chunk)
			}

			// Should still return the main content without sources
			expect(messages.some((m) => m.type === "text" && m.text === "test response")).toBe(true)
			expect(messages.some((m) => m.type === "text" && m.text?.includes("Sources:"))).toBe(false)
		})

		it("should handle malformed grounding metadata", async () => {
			const options = {
				apiProvider: "gemini",
				enableGrounding: true,
			} as ApiHandlerOptions
			const handler = new GeminiHandler(options)

			const mockStream = async function* () {
				yield {
					candidates: [
						{
							groundingMetadata: {
								groundingChunks: [
									{ web: null }, // Missing URI
									{ web: { uri: "https://example.com", title: "Example Site" } }, // Valid
									{}, // Missing web property entirely
								],
							},
							content: { parts: [{ text: "test response" }] },
						},
					],
					usageMetadata: { promptTokenCount: 10, candidatesTokenCount: 5 },
				}
			}

			const stub = vi.fn().mockReturnValue(mockStream())
			// @ts-ignore access private client
			handler["client"].models.generateContentStream = stub

			const messages = []
			for await (const chunk of handler.createMessage("test", [] as any)) {
				messages.push(chunk)
			}

			// Should have the text response
			const textMessage = messages.find((m) => m.type === "text")
			expect(textMessage).toBeDefined()
			if (textMessage && "text" in textMessage) {
				expect(textMessage.text).toBe("test response")
			}

			// Should have grounding chunk with only valid sources
			const groundingMessage = messages.find((m) => m.type === "grounding")
			expect(groundingMessage).toBeDefined()
			if (groundingMessage && "sources" in groundingMessage) {
				expect(groundingMessage.sources).toHaveLength(1)
				expect(groundingMessage.sources[0].url).toBe("https://example.com")
				expect(groundingMessage.sources[0].title).toBe("Example Site")
			}
		})

		it("should handle API errors when tools are enabled", async () => {
			const options = {
				apiProvider: "gemini",
				enableUrlContext: true,
				enableGrounding: true,
			} as ApiHandlerOptions
			const handler = new GeminiHandler(options)

			const mockError = new Error("API rate limit exceeded")
			const stub = vi.fn().mockRejectedValue(mockError)
			// @ts-ignore access private client
			handler["client"].models.generateContentStream = stub

			await expect(async () => {
				const generator = handler.createMessage("test", [] as any)
				await generator.next()
			}).rejects.toThrow(t("common:errors.gemini.generate_stream", { error: "API rate limit exceeded" }))
		})
	})

	describe("allowedFunctionNames support", () => {
		const testTools = [
			{
				type: "function" as const,
				function: {
					name: "read_file",
					description: "Read a file",
					parameters: { type: "object", properties: {} },
				},
			},
			{
				type: "function" as const,
				function: {
					name: "write_to_file",
					description: "Write to a file",
					parameters: { type: "object", properties: {} },
				},
			},
			{
				type: "function" as const,
				function: {
					name: "execute_command",
					description: "Execute a command",
					parameters: { type: "object", properties: {} },
				},
			},
		]

		it("should pass allowedFunctionNames to toolConfig when provided", async () => {
			const options = {
				apiProvider: "gemini",
			} as ApiHandlerOptions
			const handler = new GeminiHandler(options)
			const stub = vi.fn().mockReturnValue((async function* () {})())
			// @ts-ignore access private client
			handler["client"].models.generateContentStream = stub

			await handler
				.createMessage("test", [] as any, {
					taskId: "test-task",
					tools: testTools,
					allowedFunctionNames: ["read_file", "write_to_file"],
				})
				.next()

			const config = stub.mock.calls[0][0].config
			expect(config.toolConfig).toEqual({
				functionCallingConfig: {
					mode: FunctionCallingConfigMode.ANY,
					allowedFunctionNames: ["read_file", "write_to_file"],
				},
			})
		})

		it("should include all tools but restrict callable functions via allowedFunctionNames", async () => {
			const options = {
				apiProvider: "gemini",
			} as ApiHandlerOptions
			const handler = new GeminiHandler(options)
			const stub = vi.fn().mockReturnValue((async function* () {})())
			// @ts-ignore access private client
			handler["client"].models.generateContentStream = stub

			await handler
				.createMessage("test", [] as any, {
					taskId: "test-task",
					tools: testTools,
					allowedFunctionNames: ["read_file"],
				})
				.next()

			const config = stub.mock.calls[0][0].config
			// All tools should be passed to the model
			expect(config.tools[0].functionDeclarations).toHaveLength(3)
			// But only read_file should be allowed to be called
			expect(config.toolConfig.functionCallingConfig.allowedFunctionNames).toEqual(["read_file"])
		})

		it("should take precedence over tool_choice when allowedFunctionNames is provided", async () => {
			const options = {
				apiProvider: "gemini",
			} as ApiHandlerOptions
			const handler = new GeminiHandler(options)
			const stub = vi.fn().mockReturnValue((async function* () {})())
			// @ts-ignore access private client
			handler["client"].models.generateContentStream = stub

			await handler
				.createMessage("test", [] as any, {
					taskId: "test-task",
					tools: testTools,
					tool_choice: "auto",
					allowedFunctionNames: ["read_file"],
				})
				.next()

			const config = stub.mock.calls[0][0].config
			// allowedFunctionNames should take precedence - mode should be ANY, not AUTO
			expect(config.toolConfig.functionCallingConfig.mode).toBe(FunctionCallingConfigMode.ANY)
			expect(config.toolConfig.functionCallingConfig.allowedFunctionNames).toEqual(["read_file"])
		})

		it("should fall back to tool_choice when allowedFunctionNames is empty", async () => {
			const options = {
				apiProvider: "gemini",
			} as ApiHandlerOptions
			const handler = new GeminiHandler(options)
			const stub = vi.fn().mockReturnValue((async function* () {})())
			// @ts-ignore access private client
			handler["client"].models.generateContentStream = stub

			await handler
				.createMessage("test", [] as any, {
					taskId: "test-task",
					tools: testTools,
					tool_choice: "auto",
					allowedFunctionNames: [],
				})
				.next()

			const config = stub.mock.calls[0][0].config
			// Empty allowedFunctionNames should fall back to tool_choice behavior
			expect(config.toolConfig.functionCallingConfig.mode).toBe(FunctionCallingConfigMode.AUTO)
			expect(config.toolConfig.functionCallingConfig.allowedFunctionNames).toBeUndefined()
		})

		it("should not set toolConfig when allowedFunctionNames is undefined and no tool_choice", async () => {
			const options = {
				apiProvider: "gemini",
			} as ApiHandlerOptions
			const handler = new GeminiHandler(options)
			const stub = vi.fn().mockReturnValue((async function* () {})())
			// @ts-ignore access private client
			handler["client"].models.generateContentStream = stub

			await handler
				.createMessage("test", [] as any, {
					taskId: "test-task",
					tools: testTools,
				})
				.next()

			const config = stub.mock.calls[0][0].config
			// No toolConfig should be set when neither allowedFunctionNames nor tool_choice is provided
			expect(config.toolConfig).toBeUndefined()
		})

 it("stream parses thoughts, function calls, grounding and usage and captures responseId/signature", async () => {
   const options = { apiProvider: "gemini" } as ApiHandlerOptions
   const handler = new GeminiHandler(options)
 
   // Build a mock streaming response that includes:
   // - a thought part with thoughtSignature
   // - a functionCall part (should emit two partials)
   // - a final response chunk with responseId and candidate.groundingMetadata and usageMetadata
   // - a fallback plain-text chunk (no candidates)
   const mockStream = async function* () {
     // Thought chunk
     yield {
       candidates: [
         {
           content: {
             parts: [{ thought: true, text: "I am thinking", thoughtSignature: "sig-42" }],
           },
         },
       ],
     }
 
     // Function call + final structural info
     yield {
       candidates: [
         {
           content: {
             parts: [{ functionCall: { name: "doThing", args: { foo: "bar" } } }],
           },
           finishReason: "stop",
           groundingMetadata: {
             groundingChunks: [{ web: { uri: "https://example.com", title: "Example" } }],
           },
         },
       ],
       // responseId attached at chunk level is picked up when candidate.finishReason is present
       responseId: "resp-42",
       usageMetadata: {
         promptTokenCount: 10,
         candidatesTokenCount: 20,
         cachedContentTokenCount: 2,
         thoughtsTokenCount: 3,
       },
     }
 
     // Fallback plain-text chunk
     yield { text: "fallback plain text" }
   }
 
   const stub = vi.fn().mockReturnValue(mockStream())
   // @ts-ignore access private client
   handler["client"].models.generateContentStream = stub
 
   const received: any[] = []
   for await (const chunk of handler.createMessage("sys", [] as any)) {
     received.push(chunk)
   }
 
   // Should have captured the thought signature
   expect(handler.getThoughtSignature()).toBe("sig-42")
   // Should have captured the response id
   expect(handler.getResponseId()).toBe("resp-42")
 
   // Should include a reasoning chunk from the thought
   expect(received.some((r) => r.type === "reasoning" && r.text === "I am thinking")).toBe(true)
 
   // Should include two partial tool call chunks for the function call
   const toolPartials = received.filter((r) => r.type === "tool_call_partial")
   expect(toolPartials.length).toBeGreaterThanOrEqual(2)
   // First partial should contain the name
   expect(toolPartials[0].name).toBe("doThing")
   // Second partial should contain the arguments JSON
   expect(JSON.parse(toolPartials[1].arguments)).toEqual({ foo: "bar" })
 
   // Should include grounding source emitted after stream end
   const grounding = received.find((r) => r.type === "grounding")
   expect(grounding).toBeDefined()
   if (grounding) {
     expect(grounding.sources[0].url).toBe("https://example.com")
     expect(grounding.sources[0].title).toBe("Example")
   }
 
   // Should include a usage chunk with numeric token fields
   const usage = received.find((r) => r.type === "usage")
   expect(usage).toBeDefined()
   if (usage) {
     expect(typeof usage.inputTokens).toBe("number")
     expect(typeof usage.outputTokens).toBe("number")
     expect(typeof usage.reasoningTokens).toBe("number")
     // totalCost may be a number or undefined depending on model info; allow both
     expect(typeof usage.totalCost === "number" || usage.totalCost === undefined).toBe(true)
   }
 
   // Should include fallback plain text chunk
   expect(received.some((r) => r.type === "text" && r.text === "fallback plain text")).toBe(true)
 })


 it("handles tool_choice variants: required -> ANY, function object -> allowedFunctionNames, unknown -> AUTO", async () => {
   const options = { apiProvider: "gemini" } as ApiHandlerOptions
   const handler = new GeminiHandler(options)
   const stub = vi.fn().mockReturnValue((async function* () {})())
   // @ts-ignore access private client
   handler["client"].models.generateContentStream = stub
 
   // required -> ANY
   await handler.createMessage("test", [] as any, { tool_choice: "required", tools: [] as any }).next()
   let config = stub.mock.calls[0][0].config
   expect(config.toolConfig.functionCallingConfig.mode).toBe(FunctionCallingConfigMode.ANY)
 
   // function object -> allowedFunctionNames + ANY
   stub.mockClear()
   await handler
     .createMessage("test", [] as any, {
       tool_choice: { type: "function", function: { name: "doThing" } } as any,
       tools: [],
     })
     .next()
   config = stub.mock.calls[0][0].config
   expect(config.toolConfig.functionCallingConfig.mode).toBe(FunctionCallingConfigMode.ANY)
   expect(config.toolConfig.functionCallingConfig.allowedFunctionNames).toEqual(["doThing"])
 
   // unknown -> AUTO fallback
   stub.mockClear()
   await handler.createMessage("test", [] as any, { tool_choice: "something-unknown", tools: [] as any }).next()
   config = stub.mock.calls[0][0].config
   expect(config.toolConfig.functionCallingConfig.mode).toBe(FunctionCallingConfigMode.AUTO)
 })


 it("calculateCost uses tier pricing, includes cache read costs and returns undefined when prices missing", () => {
   const options = {
     apiProvider: "gemini",
   } as ApiHandlerOptions
   const handler = new GeminiHandler(options)
 
   // Case: tiers provided and matching tier overrides prices
   const infoWithTiers: any = {
     tiers: [
       { contextWindow: 1000, inputPrice: 2, outputPrice: 4, cacheReadsPrice: 1 },
       { contextWindow: 2000, inputPrice: 1.5, outputPrice: 3 },
     ],
   }
 
   const inputTokens = 500
   const outputTokens = 200
   const cacheReadTokens = 50
   const reasoningTokens = 10
 
   const cost = handler.calculateCost({
     info: infoWithTiers,
     inputTokens,
     outputTokens,
     cacheReadTokens,
     reasoningTokens,
   })
 
   // Manually compute expected cost:
   // uncachedInputTokens = 500 - 50 = 450
   // input cost = 2 * (450 / 1_000_000) = 0.0009
   // billed output = 200 + 10 = 210
   // output cost = 4 * (210 / 1_000_000) = 0.00084
   // cache read cost = 1 * (50 / 1_000_000) = 0.00005
   const expected = 2 * (450 / 1_000_000) + 4 * (210 / 1_000_000) + 1 * (50 / 1_000_000)
   expect(typeof cost).toBe("number")
   if (typeof cost === "number") {
     expect(cost).toBeCloseTo(expected, 12)
   }
 
   // Case: missing input/output prices -> undefined
   const infoMissingPrices: any = {}
   const undefinedCost = handler.calculateCost({
     info: infoMissingPrices,
     inputTokens: 10,
     outputTokens: 5,
   })
   expect(undefinedCost).toBeUndefined()
 })


 it("completePrompt appends citations when grounding metadata is present", async () => {
   const options = {
     apiProvider: "gemini",
   } as ApiHandlerOptions
   const handler = new GeminiHandler(options)
 
   const stub = vi.fn().mockResolvedValue({
     text: "Answer text",
     candidates: [
       {
         groundingMetadata: {
           groundingChunks: [
             { web: { uri: "https://source.example", title: "Source Title" } },
           ],
         },
       },
     ],
   })
   // @ts-ignore access private client
   handler["client"].models.generateContent = stub
 
   const res = await handler.completePrompt("prompt")
   // Should contain the original text
   expect(res.startsWith("Answer text")).toBe(true)
   // Should include the translated "sources" label and the citation link [1](url)
   const sourcesLabel = t("common:errors.gemini.sources")
   expect(res).toContain(sourcesLabel)
   expect(res).toContain("[1](https://source.example)")
 })

	})
})
