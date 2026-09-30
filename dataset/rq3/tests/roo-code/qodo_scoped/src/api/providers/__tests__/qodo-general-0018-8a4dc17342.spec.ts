const mockCaptureException = vi.hoisted(() => vi.fn())

// Mock BedrockRuntimeClient and commands
const mockSend = vi.fn()

// Mock AWS SDK credential providers
vi.mock("@aws-sdk/credential-providers", () => {
	return {
		fromIni: vi.fn().mockReturnValue({
			accessKeyId: "profile-access-key",
			secretAccessKey: "profile-secret-key",
		}),
	}
})

vi.mock("@aws-sdk/client-bedrock-runtime", () => ({
	BedrockRuntimeClient: vi.fn().mockImplementation(() => ({
		send: mockSend,
	})),
	ConverseStreamCommand: vi.fn(),
	ConverseCommand: vi.fn(),
}))

import { AwsBedrockHandler } from "../bedrock"
import { Anthropic } from "@anthropic-ai/sdk"

describe("AwsBedrockHandler Error Handling", () => {
	let handler: AwsBedrockHandler

	beforeEach(() => {
		vi.clearAllMocks()
		mockCaptureException.mockClear()
		handler = new AwsBedrockHandler({
			apiModelId: "anthropic.claude-3-5-sonnet-20241022-v2:0",
			awsAccessKey: "test-access-key",
			awsSecretKey: "test-secret-key",
			awsRegion: "us-east-1",
		})
	})

	const createMockError = (options: {
		message?: string
		name?: string
		status?: number
		__type?: string
		$metadata?: {
			httpStatusCode?: number
			requestId?: string
			extendedRequestId?: string
			cfId?: string
			[key: string]: any // Allow additional properties
		}
	}): Error => {
		const error = new Error(options.message || "Test error") as any
		if (options.name) error.name = options.name
		if (options.status) error.status = options.status
		if (options.__type) error.__type = options.__type
		if (options.$metadata) error.$metadata = options.$metadata
		return error
	}

	describe("Throttling Error Detection", () => {
		it("should detect throttling from HTTP 429 status code", async () => {
			const throttleError = createMockError({
				message: "Request failed",
				status: 429,
			})

			mockSend.mockRejectedValueOnce(throttleError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("throttled or rate limited")
			} catch (error) {
				expect(error.message).toContain("throttled or rate limited")
			}
		})

		it("should detect throttling from AWS SDK $metadata.httpStatusCode", async () => {
			const throttleError = createMockError({
				message: "Request failed",
				$metadata: { httpStatusCode: 429 },
			})

			mockSend.mockRejectedValueOnce(throttleError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("throttled or rate limited")
			} catch (error) {
				expect(error.message).toContain("throttled or rate limited")
			}
		})

		it("should detect throttling from ThrottlingException name", async () => {
			const throttleError = createMockError({
				message: "Request failed",
				name: "ThrottlingException",
			})

			mockSend.mockRejectedValueOnce(throttleError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("throttled or rate limited")
			} catch (error) {
				expect(error.message).toContain("throttled or rate limited")
			}
		})

		it("should detect throttling from __type field", async () => {
			const throttleError = createMockError({
				message: "Request failed",
				__type: "ThrottlingException",
			})

			mockSend.mockRejectedValueOnce(throttleError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("throttled or rate limited")
			} catch (error) {
				expect(error.message).toContain("throttled or rate limited")
			}
		})

		it("should detect throttling from 'Bedrock is unable to process your request' message", async () => {
			const throttleError = createMockError({
				message: "Bedrock is unable to process your request",
			})

			mockSend.mockRejectedValueOnce(throttleError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("throttled or rate limited")
			} catch (error) {
				expect(error.message).toMatch(/throttled or rate limited/)
			}
		})

		it("should detect throttling from various message patterns", async () => {
			const throttlingMessages = [
				"Request throttled",
				"Rate limit exceeded",
				"Too many requests",
				"Service unavailable due to high demand",
				"Server is overloaded",
				"System is busy",
				"Please wait and try again",
			]

			for (const message of throttlingMessages) {
				const throttleError = createMockError({ message })
				mockSend.mockRejectedValueOnce(throttleError)

				try {
					await handler.completePrompt("test")
					// Should not reach here as completePrompt should throw
					throw new Error("Expected error to be thrown")
				} catch (error) {
					expect(error.message).toContain("throttled or rate limited")
				}
			}
		})

		it("should display appropriate error information for throttling errors", async () => {
			const throttlingError = createMockError({
				message: "Bedrock is unable to process your request",
				name: "ThrottlingException",
				status: 429,
				$metadata: {
					httpStatusCode: 429,
					requestId: "12345-abcde-67890",
					extendedRequestId: "extended-12345",
					cfId: "cf-12345",
				},
			})

			mockSend.mockRejectedValueOnce(throttlingError)

			try {
				await handler.completePrompt("test")
				throw new Error("Expected error to be thrown")
			} catch (error) {
				// Should contain the main error message
				expect(error.message).toContain("throttled or rate limited")
			}
		})
	})

	describe("Service Quota Exceeded Detection", () => {
		it("should detect service quota exceeded errors", async () => {
			const quotaError = createMockError({
				message: "Service quota exceeded for model requests",
			})

			mockSend.mockRejectedValueOnce(quotaError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("Service quota exceeded")
			} catch (error) {
				expect(error.message).toContain("Service quota exceeded")
			}
		})
	})

	describe("Model Not Ready Detection", () => {
		it("should detect model not ready errors", async () => {
			const modelError = createMockError({
				message: "Model is not ready, please try again later",
			})

			mockSend.mockRejectedValueOnce(modelError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("Model is not ready")
			} catch (error) {
				expect(error.message).toContain("Model is not ready")
			}
		})
	})

	describe("Internal Server Error Detection", () => {
		it("should detect internal server errors", async () => {
			const serverError = createMockError({
				message: "Internal server error occurred",
			})

			mockSend.mockRejectedValueOnce(serverError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("internal server error")
			} catch (error) {
				expect(error.message).toContain("internal server error")
			}
		})
	})

	describe("Token Limit Detection", () => {
		it("should detect enhanced token limit errors", async () => {
			const tokenErrors = [
				"Too many tokens in request",
				"Token limit exceeded",
				"Maximum context length reached",
				"Context length exceeds limit",
			]

			for (const message of tokenErrors) {
				const tokenError = createMockError({ message })
				mockSend.mockRejectedValueOnce(tokenError)

				try {
					await handler.completePrompt("test")
					// Should not reach here as completePrompt should throw
					throw new Error("Expected error to be thrown")
				} catch (error) {
					// Either "Too many tokens" for token-specific errors or "throttled" for limit-related errors
					expect(error.message).toMatch(/Too many tokens|throttled or rate limited/)
				}
			}
		})
	})

	describe("Streaming Context Error Handling", () => {
		it("should handle throttling errors in streaming context", async () => {
			const throttleError = createMockError({
				message: "Bedrock is unable to process your request",
				status: 429,
			})

			const mockStream = {
				[Symbol.asyncIterator]() {
					return {
						async next() {
							throw throttleError
						},
					}
				},
			}

			mockSend.mockResolvedValueOnce({ stream: mockStream })

			const generator = handler.createMessage("system", [{ role: "user", content: "test" }])

			// For throttling errors, it should throw immediately without yielding chunks
			// This allows the retry mechanism to catch and handle it
			await expect(async () => {
				for await (const chunk of generator) {
					// Should not yield any chunks for throttling errors
				}
			}).rejects.toThrow("Bedrock is unable to process your request")
		})

		it("should yield error chunks for non-throttling errors in streaming context", async () => {
			const genericError = createMockError({
				message: "Some other error",
				status: 500,
			})

			const mockStream = {
				[Symbol.asyncIterator]() {
					return {
						async next() {
							throw genericError
						},
					}
				},
			}

			mockSend.mockResolvedValueOnce({ stream: mockStream })

			const generator = handler.createMessage("system", [{ role: "user", content: "test" }])

			const chunks: any[] = []
			try {
				for await (const chunk of generator) {
					chunks.push(chunk)
				}
			} catch (error) {
				// Expected to throw after yielding chunks
			}

			// Should have yielded error chunks before throwing for non-throttling errors
			expect(
				chunks.some((chunk) => chunk.type === "text" && chunk.text && chunk.text.includes("Some other error")),
			).toBe(true)
		})
	})

	describe("Error Priority and Specificity", () => {
		it("should prioritize HTTP status codes over message patterns", async () => {
			// Error with both 429 status and generic message should be detected as throttling
			const mixedError = createMockError({
				message: "Some generic error message",
				status: 429,
			})

			mockSend.mockRejectedValueOnce(mixedError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("throttled or rate limited")
			} catch (error) {
				expect(error.message).toContain("throttled or rate limited")
			}
		})

		it("should prioritize AWS error types over message patterns", async () => {
			// Error with ThrottlingException name but different message should still be throttling
			const specificError = createMockError({
				message: "Some other error occurred",
				name: "ThrottlingException",
			})

			mockSend.mockRejectedValueOnce(specificError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("throttled or rate limited")
			} catch (error) {
				expect(error.message).toContain("throttled or rate limited")
			}
		})
	})

	describe("Unknown Error Fallback", () => {
		it("should still show unknown error for truly unrecognized errors", async () => {
			const unknownError = createMockError({
				message: "Something completely unexpected happened",
			})

			mockSend.mockRejectedValueOnce(unknownError)

			try {
				const result = await handler.completePrompt("test")
				expect(result).toContain("Unknown Error")
			} catch (error) {
				expect(error.message).toContain("Unknown Error")
			}
		})
	})

	describe("Enhanced Error Throw for Retry System", () => {
		it("should throw enhanced error messages for completePrompt to display in retry system", async () => {
			const throttlingError = createMockError({
				message: "Too many tokens, rate limited",
				status: 429,
				$metadata: {
					httpStatusCode: 429,
					requestId: "test-request-id-12345",
				},
			})
			mockSend.mockRejectedValueOnce(throttlingError)

			try {
				await handler.completePrompt("test")
				throw new Error("Expected error to be thrown")
			} catch (error) {
				// Should contain the verbose message template
				expect(error.message).toContain("Request was throttled or rate limited")
				// Should preserve original error properties
				expect((error as any).status).toBe(429)
				expect((error as any).$metadata.requestId).toBe("test-request-id-12345")
			}
		})

		it("should throw enhanced error messages for createMessage streaming to display in retry system", async () => {
			const tokenError = createMockError({
				message: "Too many tokens in request",
				name: "ValidationException",
				$metadata: {
					httpStatusCode: 400,
					requestId: "token-error-id-67890",
					extendedRequestId: "extended-12345",
				},
			})

			const mockStream = {
				[Symbol.asyncIterator]() {
					return {
						async next() {
							throw tokenError
						},
					}
				},
			}

			mockSend.mockResolvedValueOnce({ stream: mockStream })

			try {
				const stream = handler.createMessage("system", [{ role: "user", content: "test" }])
				for await (const chunk of stream) {
					// Should not reach here as it should throw an error
				}
				throw new Error("Expected error to be thrown")
			} catch (error) {
				// Should contain error codes (note: this will be caught by the non-throttling error path)
				expect(error.message).toContain("Too many tokens")
				// Should preserve original error properties
				expect(error.name).toBe("ValidationException")
				expect((error as any).$metadata.requestId).toBe("token-error-id-67890")
			}
		})
	})

	describe("Edge Case Test Coverage", () => {
		it("should handle concurrent throttling errors correctly", async () => {
			const throttlingError = createMockError({
				message: "Bedrock is unable to process your request",
				status: 429,
			})

			// Setup multiple concurrent requests that will all fail with throttling
			mockSend.mockRejectedValue(throttlingError)

			// Execute multiple concurrent requests
			const promises = Array.from({ length: 5 }, () => handler.completePrompt("test"))

			// All should throw with throttling error
			const results = await Promise.allSettled(promises)

			results.forEach((result) => {
				expect(result.status).toBe("rejected")
				if (result.status === "rejected") {
					expect(result.reason.message).toContain("throttled or rate limited")
				}
			})
		})

		it("should handle mixed error scenarios with both throttling and other indicators", async () => {
			// Error with both 429 status (throttling) and validation error message
			const mixedError = createMockError({
				message: "ValidationException: Your input is invalid, but also rate limited",
				name: "ValidationException",
				status: 429,
				$metadata: {
					httpStatusCode: 429,
					requestId: "mixed-error-id",
				},
			})

			mockSend.mockRejectedValueOnce(mixedError)

			try {
				await handler.completePrompt("test")
			} catch (error) {
				// Should be treated as throttling due to 429 status taking priority
				expect(error.message).toContain("throttled or rate limited")
				// Should still preserve metadata
				expect((error as any).$metadata?.requestId).toBe("mixed-error-id")
			}
		})

		it("should handle rapid successive retries in streaming context", async () => {
			const throttlingError = createMockError({
				message: "ThrottlingException",
				name: "ThrottlingException",
			})

			// Mock stream that throws immediately
			const mockStream = {
				// eslint-disable-next-line require-yield
				[Symbol.asyncIterator]: async function* () {
					throw throttlingError
				},
			}

			mockSend.mockResolvedValueOnce({ stream: mockStream })

			const messages: Anthropic.Messages.MessageParam[] = [{ role: "user", content: "test" }]

			try {
				// Should throw immediately without yielding any chunks
				const stream = handler.createMessage("", messages)
				const chunks = []
				for await (const chunk of stream) {
					chunks.push(chunk)
				}
				// Should not reach here
				expect(chunks).toHaveLength(0)
			} catch (error) {
				// Error should be thrown immediately for retry mechanism
				// The error might be a TypeError if the stream iterator fails
				expect(error).toBeDefined()
				// The important thing is that it throws immediately without yielding chunks
			}
		})

		it("should validate error properties exist before accessing them", async () => {
			// Error with unusual structure
			const unusualError = {
				message: "Error with unusual structure",
				// Missing typical properties like name, status, etc.
			}

			mockSend.mockRejectedValueOnce(unusualError)

			try {
				await handler.completePrompt("test")
			} catch (error) {
				// Should handle gracefully without accessing undefined properties
				expect(error.message).toContain("Unknown Error")
				// Should not have undefined values in the error message
				expect(error.message).not.toContain("undefined")
			}
		})

  it("parseBaseModelId removes global. prefix and region helpers return fallbacks", () => {
    // parseBaseModelId should strip global. prefix
    const result = (handler as any).parseBaseModelId("global.my-custom-model")
    expect(result).toBe("my-custom-model")
  
    // Empty modelId returns empty
    const empty = (handler as any).parseBaseModelId("")
    expect(empty).toBe("")
  
    // Static region prefix lookup for an unknown region should be undefined
    const prefix = (AwsBedrockHandler as any).getPrefixForRegion("some-unknown-region-1")
    expect(prefix).toBeUndefined()
  
    // Static isSystemInferenceProfile for an arbitrary string should be false
    const isSystem = (AwsBedrockHandler as any).isSystemInferenceProfile("not-a-real-prefix")
    expect(isSystem).toBe(false)
  })


  it("should throw INVALID_ARN_FORMAT when awsCustomArn is invalid", () => {
    const invalidArn = "this-is-not-a-valid-arn"
    expect(() => {
      // Provide minimal other settings to satisfy constructor
      // The constructor should call parseArn and throw with the expected prefix
      // eslint-disable-next-line no-new
      new AwsBedrockHandler({
        apiModelId: "anthropic.claude-3-5-sonnet-20241022-v2:0",
        awsRegion: "us-east-1",
        awsCustomArn: invalidArn,
      } as any)
    }).toThrow(/^INVALID_ARN_FORMAT:/)
  })


  it("convertToolsForBedrock, convertToolChoiceForBedrock, removeCachePoints, and parseBaseModelId behaviors", () => {
    // convertToolChoiceForBedrock: string forms
    const noneChoice = (handler as any).convertToolChoiceForBedrock("none")
    expect(noneChoice).toBeUndefined()
  
    const autoChoice = (handler as any).convertToolChoiceForBedrock("auto")
    expect(autoChoice).toHaveProperty("auto")
  
    const requiredChoice = (handler as any).convertToolChoiceForBedrock("required")
    expect(requiredChoice).toHaveProperty("any")
  
    // convertToolChoiceForBedrock: object function form
    const fnChoice = (handler as any).convertToolChoiceForBedrock({ type: "function", function: { name: "doIt" } })
    expect(fnChoice).toHaveProperty("tool")
    expect(fnChoice.tool).toHaveProperty("name", "doIt")
  
    // convertToolsForBedrock: should only include type === "function" and map fields
    const openAiTool = {
      type: "function",
      function: {
        name: "testFunc",
        description: "does testing",
        parameters: { type: ["string", "null"] }, // ensure normalizeToolSchema is exercised
      },
    }
    const converted = (handler as any).convertToolsForBedrock([openAiTool, { type: "other" }])
    expect(Array.isArray(converted)).toBe(true)
    expect(converted.length).toBe(1)
    expect(converted[0].toolSpec).toHaveProperty("name", "testFunc")
    expect(converted[0].toolSpec).toHaveProperty("description", "does testing")
    expect(converted[0].toolSpec.inputSchema).toHaveProperty("json")
  
    // removeCachePoints should strip cachePoint property from content arrays
    const contentIn = [{ cachePoint: { type: "default" }, text: "keep" }, { text: "no-cache" }]
    const cleaned = (handler as any).removeCachePoints(contentIn)
    expect(Array.isArray(cleaned)).toBe(true)
    expect(cleaned[0]).not.toHaveProperty("cachePoint")
    expect(cleaned[0].text).toBe("keep")
    expect(cleaned[1].text).toBe("no-cache")
  
    // parseBaseModelId should strip global. prefix
    const base = (handler as any).parseBaseModelId("global.anthropic.claude-3")
    expect(base).toBe("anthropic.claude-3")
  })


  it("should parse various stream events into expected chunk types", async () => {
    // Build an async iterable stream that yields a sequence of various event shapes
    const mockStream = {
      [Symbol.asyncIterator]: async function* () {
        // metadata usage event
        yield { metadata: { usage: { inputTokens: 1, outputTokens: 2, cacheReadInputTokens: 3 } } }
  
        // promptRouter trace with invokedModelId and usage - will cause getModelById to be called
        yield {
          trace: {
            promptRouter: {
              invokedModelId: "arn:aws:bedrock:us-west-2:123456789012:foundation-model/anthropic.claude-3",
              usage: { inputTokens: 4, outputTokens: 5, cacheReadTokens: 6 },
            },
          },
        }
  
        // contentBlockStart: reasoning content with index > 0 (produces newline then text)
        yield {
          contentBlockStart: {
            contentBlockIndex: 1,
            contentBlock: { reasoningContent: { text: "reasoning-start-text" } },
          },
        }
  
        // contentBlockStart: thinking block (newer contentBlock structure) with index > 0
        yield {
          contentBlockStart: {
            contentBlockIndex: 2,
            contentBlock: { type: "thinking", thinking: "thinking-new-structure" },
          },
        }
  
        // contentBlockStart: alternative older structure content_block
        yield {
          contentBlockStart: {
            contentBlockIndex: 0,
            content_block: { type: "thinking", thinking: "thinking-old-structure" },
          },
        }
  
        // contentBlockStart: tool use via start.toolUse
        yield {
          contentBlockStart: {
            contentBlockIndex: 3,
            start: { toolUse: { toolUseId: "tool-use-1", name: "coolTool" } },
          },
        }
  
        // contentBlockStart: simple text via start.text
        yield {
          contentBlockStart: {
            start: { text: "simple text here" },
          },
        }
  
        // contentBlockDelta: reasoningContent delta
        yield {
          contentBlockDelta: {
            delta: { reasoningContent: { text: "delta-reasoning" } },
          },
        }
  
        // contentBlockDelta: toolUse.input delta
        yield {
          contentBlockDelta: {
            contentBlockIndex: 6,
            delta: { toolUse: { input: '{"param":42}' } },
          },
        }
  
        // contentBlockDelta: thinking_delta older structure
        yield {
          contentBlockDelta: {
            delta: { type: "thinking_delta", thinking: "delta-thinking" },
          },
        }
  
        // contentBlockDelta: regular text delta
        yield {
          contentBlockDelta: {
            delta: { text: "delta-plain-text" },
          },
        }
  
        // messageStart and messageStop (should be ignored / produce no output)
        yield { messageStart: { role: "assistant" } }
        yield { messageStop: { stopReason: "end_turn" } }
  
        // End of stream
      },
    }
  
    mockSend.mockResolvedValueOnce({ stream: mockStream })
  
    const messages = [{ role: "user", content: "hello" }]
    const generator = handler.createMessage("system prompt", messages as any)
  
    const received: any[] = []
    for await (const chunk of generator) {
      received.push(chunk)
    }
  
    // Assertions across the produced chunks
    expect(received.some((c) => c.type === "usage" && c.inputTokens === 1 && c.outputTokens === 2)).toBe(true)
    // Router usage should be reflected
    expect(received.some((c) => c.type === "usage" && c.inputTokens === 4 && c.cacheReadTokens === 6)).toBe(true)
    // Reasoning content from contentBlockStart should be present
    expect(received.some((c) => c.type === "reasoning" && c.text.includes("reasoning-start-text"))).toBe(true)
    // Thinking blocks (new and old) should appear
    expect(received.some((c) => c.type === "reasoning" && c.text.includes("thinking-new-structure"))).toBe(true)
    expect(received.some((c) => c.type === "reasoning" && c.text.includes("thinking-old-structure"))).toBe(true)
    // Tool use partial start should be emitted
    expect(received.some((c) => c.type === "tool_call_partial" && c.id === "tool-use-1" && c.name === "coolTool")).toBe(true)
    // Start.text should be emitted as text
    expect(received.some((c) => c.type === "text" && c.text === "simple text here")).toBe(true)
    // Delta reasoning
    expect(received.some((c) => c.type === "reasoning" && c.text === "delta-reasoning")).toBe(true)
    // Tool use delta with arguments should be emitted
    expect(received.some((c) => c.type === "tool_call_partial" && typeof c.arguments === "string" && c.arguments.includes('"param":42'))).toBe(true)
    // Thinking delta should appear
    expect(received.some((c) => c.type === "reasoning" && c.text === "delta-thinking")).toBe(true)
    // Plain text delta should appear
    expect(received.some((c) => c.type === "text" && c.text === "delta-plain-text")).toBe(true)
  })


  it("removeCachePoints should strip cachePoint entries from arrays and return non-arrays as-is", () => {
    const input = [
      { cachePoint: { type: "default" }, text: "hello" },
      { text: "keep-me" },
    ]
    const cleaned = (handler as any).removeCachePoints(input)
    expect(Array.isArray(cleaned)).toBe(true)
    expect(cleaned.length).toBe(2)
    expect(cleaned[0].cachePoint).toBeUndefined()
    expect(cleaned[0].text).toBe("hello")
    expect(cleaned[1].text).toBe("keep-me")
  
    // Non-array input should be returned unchanged
    const notArray = "a simple string"
    const unchanged = (handler as any).removeCachePoints(notArray)
    expect(unchanged).toBe(notArray)
  })


  it("convertToolsForBedrock filters and maps function tools and convertToolChoiceForBedrock handles variants", () => {
    // Prepare a mix of tools: one function and one non-function
    const openAiTools = [
      {
        type: "function",
        function: {
          name: "doThing",
          description: "Does a thing",
          parameters: {
            type: "object",
            properties: {
              foo: { type: "string" },
            },
          },
        },
      },
      {
        type: "text", // should be filtered out
        function: {
          name: "notAFunction",
          description: "Should be ignored",
          parameters: {},
        },
      },
    ]
  
    const converted = (handler as any).convertToolsForBedrock(openAiTools)
    // Only the function tool should remain
    expect(Array.isArray(converted)).toBe(true)
    expect(converted.length).toBe(1)
    const t = converted[0]
    expect(t.toolSpec).toBeDefined()
    expect(t.toolSpec.name).toBe("doThing")
    expect(t.toolSpec.description).toBe("Does a thing")
    // Input schema should have been normalized into a json object
    expect(t.toolSpec.inputSchema).toBeDefined()
    expect(t.toolSpec.inputSchema.json).toBeDefined()
  
    // Test convertToolChoiceForBedrock for different forms
    // undefined/omitted -> auto
    const autoChoice = (handler as any).convertToolChoiceForBedrock(undefined)
    expect(autoChoice).toEqual({ auto: {} })
  
    // "none" string -> undefined (omit tools)
    const noneChoice = (handler as any).convertToolChoiceForBedrock("none")
    expect(noneChoice).toBeUndefined()
  
    // "required" -> any {}
    const requiredChoice = (handler as any).convertToolChoiceForBedrock("required")
    expect(requiredChoice).toEqual({ any: {} })
  
    // object form with function -> tool:{name}
    const objectChoice = (handler as any).convertToolChoiceForBedrock({
      function: { name: "doThing" },
    })
    expect(objectChoice).toEqual({ tool: { name: "doThing" } })
  })


  it("parseArn should parse valid ARNs and report region mismatch, and reject invalid ARNs", () => {
    // Valid ARN with a different provided region -> should report region mismatch
    const arn =
      "arn:aws:bedrock:us-west-2:123456789012:foundation-model/anthropic.claude-v2"
    const result = (handler as any).parseArn(arn, "us-east-1")
  
    expect(result).toBeDefined()
    expect(result.isValid).toBe(true)
    // region should be taken from the ARN, not the passed-in region
    expect(result.region).toBe("us-west-2")
    // Because provided region differs from ARN, an errorMessage should be present describing mismatch
    expect(result.errorMessage).toContain("Region mismatch")
  
    // Invalid ARN should return isValid false and include an invalid format message
    const invalid = (handler as any).parseArn("not-an-arn")
    expect(invalid).toBeDefined()
    expect(invalid.isValid).toBe(false)
    expect(invalid.errorMessage).toMatch(/Invalid ARN format/i)
  })

	})
})
