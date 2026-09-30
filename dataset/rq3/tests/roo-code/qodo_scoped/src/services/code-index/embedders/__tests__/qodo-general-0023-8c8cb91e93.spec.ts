import type { MockedClass, MockedFunction } from "vitest"
import { describe, it, expect, beforeEach, vi } from "vitest"
import { OpenAI } from "openai"
import { OpenRouterEmbedder, OPENROUTER_DEFAULT_PROVIDER_NAME } from "../openrouter"
import { getModelDimension, getDefaultModelId } from "../../../../shared/embeddingModels"
import * as embeddingModels from "../../../../shared/embeddingModels"

// Mock the OpenAI SDK
vi.mock("openai")

// Mock i18n
vi.mock("../../../../i18n", () => ({
	t: (key: string, params?: Record<string, any>) => {
		const translations: Record<string, string> = {
			"embeddings:validation.apiKeyRequired": "validation.apiKeyRequired",
			"embeddings:authenticationFailed":
				"Failed to create embeddings: Authentication failed. Please check your OpenRouter API key.",
			"embeddings:failedWithStatus": `Failed to create embeddings after ${params?.attempts} attempts: HTTP ${params?.statusCode} - ${params?.errorMessage}`,
			"embeddings:failedWithError": `Failed to create embeddings after ${params?.attempts} attempts: ${params?.errorMessage}`,
			"embeddings:failedMaxAttempts": `Failed to create embeddings after ${params?.attempts} attempts`,
			"embeddings:textExceedsTokenLimit": `Text at index ${params?.index} exceeds maximum token limit (${params?.itemTokens} > ${params?.maxTokens}). Skipping.`,
			"embeddings:rateLimitRetry": `Rate limit hit, retrying in ${params?.delayMs}ms (attempt ${params?.attempt}/${params?.maxRetries})`,
		}
		return translations[key] || key
	},
}))

const MockedOpenAI = OpenAI as MockedClass<typeof OpenAI>

describe("OpenRouterEmbedder", () => {
	const mockApiKey = "test-api-key"
	let mockEmbeddingsCreate: MockedFunction<any>
	let mockOpenAIInstance: any

	beforeEach(() => {
		vi.clearAllMocks()
		vi.spyOn(console, "warn").mockImplementation(() => {})
		vi.spyOn(console, "error").mockImplementation(() => {})

		// Setup mock OpenAI instance
		mockEmbeddingsCreate = vi.fn()
		mockOpenAIInstance = {
			embeddings: {
				create: mockEmbeddingsCreate,
			},
		}

		MockedOpenAI.mockImplementation(() => mockOpenAIInstance)
	})

	afterEach(() => {
		vi.restoreAllMocks()
	})

	describe("constructor", () => {
		it("should create an instance with valid API key", () => {
			const embedder = new OpenRouterEmbedder(mockApiKey)
			expect(embedder).toBeInstanceOf(OpenRouterEmbedder)
		})

		it("should throw error with empty API key", () => {
			expect(() => new OpenRouterEmbedder("")).toThrow("validation.apiKeyRequired")
		})

		it("should use default model when none specified", () => {
			const embedder = new OpenRouterEmbedder(mockApiKey)
			const expectedDefault = getDefaultModelId("openrouter")
			expect(embedder.embedderInfo.name).toBe("openrouter")
		})

		it("should use custom model when specified", () => {
			const customModel = "openai/text-embedding-3-small"
			const embedder = new OpenRouterEmbedder(mockApiKey, customModel)
			expect(embedder.embedderInfo.name).toBe("openrouter")
		})

		it("should initialize OpenAI client with correct headers", () => {
			new OpenRouterEmbedder(mockApiKey)

			expect(MockedOpenAI).toHaveBeenCalledWith({
				baseURL: "https://openrouter.ai/api/v1",
				apiKey: mockApiKey,
				defaultHeaders: {
					"HTTP-Referer": "https://github.com/RooCodeInc/Roo-Code",
					"X-Title": "Roo Code",
				},
			})
		})

		it("should accept specificProvider parameter", () => {
			const embedder = new OpenRouterEmbedder(mockApiKey, undefined, undefined, "together")
			expect(embedder).toBeInstanceOf(OpenRouterEmbedder)
		})

		it("should ignore default provider name as specificProvider", () => {
			const embedder = new OpenRouterEmbedder(mockApiKey, undefined, undefined, OPENROUTER_DEFAULT_PROVIDER_NAME)
			expect(embedder).toBeInstanceOf(OpenRouterEmbedder)
		})
	})

	describe("embedderInfo", () => {
		it("should return correct embedder info", () => {
			const embedder = new OpenRouterEmbedder(mockApiKey)
			expect(embedder.embedderInfo).toEqual({
				name: "openrouter",
			})
		})
	})

	describe("createEmbeddings", () => {
		let embedder: OpenRouterEmbedder

		beforeEach(() => {
			embedder = new OpenRouterEmbedder(mockApiKey)
		})

		it("should create embeddings successfully", async () => {
			// Create base64 encoded embedding with values that can be exactly represented in Float32
			const testEmbedding = new Float32Array([0.25, 0.5, 0.75])
			const base64String = Buffer.from(testEmbedding.buffer).toString("base64")

			const mockResponse = {
				data: [
					{
						embedding: base64String,
					},
				],
				usage: {
					prompt_tokens: 5,
					total_tokens: 5,
				},
			}

			mockEmbeddingsCreate.mockResolvedValue(mockResponse)

			const result = await embedder.createEmbeddings(["test text"])

			expect(mockEmbeddingsCreate).toHaveBeenCalledWith({
				input: ["test text"],
				model: "openai/text-embedding-3-large",
				encoding_format: "base64",
			})
			expect(result.embeddings).toHaveLength(1)
			expect(result.embeddings[0]).toEqual([0.25, 0.5, 0.75])
			expect(result.usage?.promptTokens).toBe(5)
			expect(result.usage?.totalTokens).toBe(5)
		})

		it("should handle multiple texts", async () => {
			const embedding1 = new Float32Array([0.25, 0.5])
			const embedding2 = new Float32Array([0.75, 1.0])
			const base64String1 = Buffer.from(embedding1.buffer).toString("base64")
			const base64String2 = Buffer.from(embedding2.buffer).toString("base64")

			const mockResponse = {
				data: [
					{
						embedding: base64String1,
					},
					{
						embedding: base64String2,
					},
				],
				usage: {
					prompt_tokens: 10,
					total_tokens: 10,
				},
			}

			mockEmbeddingsCreate.mockResolvedValue(mockResponse)

			const result = await embedder.createEmbeddings(["text1", "text2"])

			expect(result.embeddings).toHaveLength(2)
			expect(result.embeddings[0]).toEqual([0.25, 0.5])
			expect(result.embeddings[1]).toEqual([0.75, 1.0])
		})

		it("should use custom model when provided", async () => {
			const customModel = "mistralai/mistral-embed-2312"
			const embedderWithCustomModel = new OpenRouterEmbedder(mockApiKey, customModel)

			const testEmbedding = new Float32Array([0.25, 0.5])
			const base64String = Buffer.from(testEmbedding.buffer).toString("base64")

			const mockResponse = {
				data: [
					{
						embedding: base64String,
					},
				],
				usage: {
					prompt_tokens: 5,
					total_tokens: 5,
				},
			}

			mockEmbeddingsCreate.mockResolvedValue(mockResponse)

			await embedderWithCustomModel.createEmbeddings(["test"])

			// Verify the embeddings.create was called with the custom model
			expect(mockEmbeddingsCreate).toHaveBeenCalledWith({
				input: ["test"],
				model: customModel,
				encoding_format: "base64",
			})
		})

		it("should include provider routing when specificProvider is set", async () => {
			const specificProvider = "together"
			const embedderWithProvider = new OpenRouterEmbedder(mockApiKey, undefined, undefined, specificProvider)

			const testEmbedding = new Float32Array([0.25, 0.5])
			const base64String = Buffer.from(testEmbedding.buffer).toString("base64")

			const mockResponse = {
				data: [
					{
						embedding: base64String,
					},
				],
				usage: {
					prompt_tokens: 5,
					total_tokens: 5,
				},
			}

			mockEmbeddingsCreate.mockResolvedValue(mockResponse)

			await embedderWithProvider.createEmbeddings(["test"])

			// Verify the embeddings.create was called with provider routing
			expect(mockEmbeddingsCreate).toHaveBeenCalledWith({
				input: ["test"],
				model: "openai/text-embedding-3-large",
				encoding_format: "base64",
				provider: {
					order: [specificProvider],
					only: [specificProvider],
					allow_fallbacks: false,
				},
			})
		})

		it("should not include provider routing when specificProvider is default", async () => {
			const embedderWithDefaultProvider = new OpenRouterEmbedder(
				mockApiKey,
				undefined,
				undefined,
				OPENROUTER_DEFAULT_PROVIDER_NAME,
			)

			const testEmbedding = new Float32Array([0.25, 0.5])
			const base64String = Buffer.from(testEmbedding.buffer).toString("base64")

			const mockResponse = {
				data: [
					{
						embedding: base64String,
					},
				],
				usage: {
					prompt_tokens: 5,
					total_tokens: 5,
				},
			}

			mockEmbeddingsCreate.mockResolvedValue(mockResponse)

			await embedderWithDefaultProvider.createEmbeddings(["test"])

			// Verify the embeddings.create was called without provider routing
			expect(mockEmbeddingsCreate).toHaveBeenCalledWith({
				input: ["test"],
				model: "openai/text-embedding-3-large",
				encoding_format: "base64",
			})
		})
	})

	describe("validateConfiguration", () => {
		let embedder: OpenRouterEmbedder

		beforeEach(() => {
			embedder = new OpenRouterEmbedder(mockApiKey)
		})

		it("should validate configuration successfully", async () => {
			const testEmbedding = new Float32Array([0.25, 0.5])
			const base64String = Buffer.from(testEmbedding.buffer).toString("base64")

			const mockResponse = {
				data: [
					{
						embedding: base64String,
					},
				],
				usage: {
					prompt_tokens: 1,
					total_tokens: 1,
				},
			}

			mockEmbeddingsCreate.mockResolvedValue(mockResponse)

			const result = await embedder.validateConfiguration()

			expect(result.valid).toBe(true)
			expect(result.error).toBeUndefined()
			expect(mockEmbeddingsCreate).toHaveBeenCalledWith({
				input: ["test"],
				model: "openai/text-embedding-3-large",
				encoding_format: "base64",
			})
		})

		it("should handle validation failure", async () => {
			const authError = new Error("Invalid API key")
			;(authError as any).status = 401

			mockEmbeddingsCreate.mockRejectedValue(authError)

			const result = await embedder.validateConfiguration()

			expect(result.valid).toBe(false)
			expect(result.error).toBe("embeddings:validation.authenticationFailed")
		})

		it("should validate configuration with specificProvider", async () => {
			const specificProvider = "openai"
			const embedderWithProvider = new OpenRouterEmbedder(mockApiKey, undefined, undefined, specificProvider)

			const testEmbedding = new Float32Array([0.25, 0.5])
			const base64String = Buffer.from(testEmbedding.buffer).toString("base64")

			const mockResponse = {
				data: [
					{
						embedding: base64String,
					},
				],
				usage: {
					prompt_tokens: 1,
					total_tokens: 1,
				},
			}

			mockEmbeddingsCreate.mockResolvedValue(mockResponse)

			const result = await embedderWithProvider.validateConfiguration()

			expect(result.valid).toBe(true)
			expect(result.error).toBeUndefined()
			expect(mockEmbeddingsCreate).toHaveBeenCalledWith({
				input: ["test"],
				model: "openai/text-embedding-3-large",
				encoding_format: "base64",
				provider: {
					order: [specificProvider],
					only: [specificProvider],
					allow_fallbacks: false,
				},
			})
		})
	})

	describe("integration with shared models", () => {
		it("should work with defined OpenRouter models", () => {
			const openRouterModels = [
				"openai/text-embedding-3-small",
				"openai/text-embedding-3-large",
				"openai/text-embedding-ada-002",
				"google/gemini-embedding-001",
				"mistralai/mistral-embed-2312",
				"mistralai/codestral-embed-2505",
				"qwen/qwen3-embedding-0.6b",
				"qwen/qwen3-embedding-4b",
				"qwen/qwen3-embedding-8b",
			]

			openRouterModels.forEach((model) => {
				const dimension = getModelDimension("openrouter", model)
				expect(dimension).toBeDefined()
				expect(dimension).toBeGreaterThan(0)

				const embedder = new OpenRouterEmbedder(mockApiKey, model)
				expect(embedder.embedderInfo.name).toBe("openrouter")
			})
		})

		it("should use correct default model", () => {
			const defaultModel = getDefaultModelId("openrouter")
			expect(defaultModel).toBe("openai/text-embedding-3-large")

			const dimension = getModelDimension("openrouter", defaultModel)
			expect(dimension).toBe(3072)
		})
	})

  it("should retry on 429 error then succeed and update global rate limit state", async () => {
    // Arrange: fake timers so we don't actually wait during the retry delay
    vi.useFakeTimers()
  
    // First call fails with a 429-like error, second call succeeds
    const rateLimitError: any = new Error("rate limited")
    rateLimitError.status = 429
    const successEmbedding = new Float32Array([0.4, 0.8])
    const base64String = Buffer.from(successEmbedding.buffer).toString("base64")
    const successResponse = {
      data: [
        {
          embedding: base64String,
        },
      ],
      usage: {
        prompt_tokens: 3,
        total_tokens: 3,
      },
    }
  
    mockEmbeddingsCreate
      .mockRejectedValueOnce(rateLimitError)
      .mockResolvedValueOnce(successResponse)
  
    const embedder = new OpenRouterEmbedder(mockApiKey)
  
    // Act: start the request (it will retry on 429)
    const pending = embedder.createEmbeddings(["retry-text"])
  
    // Fast-forward timers so the retry delay promise resolves immediately
    vi.runAllTimers()
  
    const result = await pending
  
    // Assert: embeddings succeeded and provider was called twice (initial failure + retry)
    expect(mockEmbeddingsCreate).toHaveBeenCalledTimes(2)
    expect(result.embeddings).toHaveLength(1)
    // Float32 conversion rounding
    expect(result.embeddings[0]).toEqual([0.4000000059604645, 0.800000011920929])
    // Global state should have been set to rate limited by the handler
    const globalState = (OpenRouterEmbedder as any).globalRateLimitState
    expect(globalState.isRateLimited).toBe(true)
    expect(globalState.rateLimitResetTime).toBeGreaterThan(Date.now())
  
    // Cleanup timers
    vi.useRealTimers()
  })


  it("should preserve numeric array embeddings when provider returns numeric arrays", async () => {
    // Arrange: provider returns numeric arrays directly
    const numericEmbedding = [1, 2, 3]
    const mockResponse = {
      data: [
        {
          embedding: numericEmbedding,
        },
      ],
      usage: {
        prompt_tokens: 1,
        total_tokens: 1,
      },
    }
    mockEmbeddingsCreate.mockResolvedValue(mockResponse)
  
    const embedder = new OpenRouterEmbedder(mockApiKey)
  
    // Act
    const result = await embedder.createEmbeddings(["text"])
  
    // Assert
    expect(mockEmbeddingsCreate).toHaveBeenCalled()
    expect(result.embeddings).toEqual([[1, 2, 3]])
    expect(result.usage?.promptTokens).toBe(1)
    expect(result.usage?.totalTokens).toBe(1)
  })


  it("should skip texts that exceed maxItemTokens and return empty embeddings", async () => {
    // Create embedder with tiny maxItemTokens so a short string will exceed it
    const smallMaxItemTokens = 1
    const embedder = new OpenRouterEmbedder(mockApiKey, undefined, smallMaxItemTokens)
  
    // Use a string of length 10: Math.ceil(10/4) = 3 > 1, so it will be skipped
    const result = await embedder.createEmbeddings(["this-will-be-too-long"])
  
    // No network call should have been made because item was skipped
    expect(mockEmbeddingsCreate).not.toHaveBeenCalled()
    expect(result.embeddings).toHaveLength(0)
    expect(result.usage).toEqual({ promptTokens: 0, totalTokens: 0 })
    // A console.warn should have been emitted for skipping the text
    expect(console.warn).toHaveBeenCalled()
  })


  it("should not prefix text if adding prefix exceeds token limit", async () => {
    // Arrange: make the model return an extremely large prefix so estimated tokens exceed limits
    const longPrefix = "A".repeat(100000)
    const embeddingModels = await import("../../../../shared/embeddingModels")
    const spyGetModelQueryPrefix = vi
      .spyOn(embeddingModels, "getModelQueryPrefix")
      .mockReturnValue(longPrefix as any)
  
    // Prepare a normal small embedding response
    const testEmbedding = new Float32Array([0.1, 0.2])
    const base64String = Buffer.from(testEmbedding.buffer).toString("base64")
    const mockResponse = {
      data: [
        {
          embedding: base64String,
        },
      ],
      usage: {
        prompt_tokens: 2,
        total_tokens: 2,
      },
    }
    mockEmbeddingsCreate.mockResolvedValue(mockResponse)
  
    const embedder = new OpenRouterEmbedder(mockApiKey)
  
    // Act
    const result = await embedder.createEmbeddings(["short-text"])
  
    // Assert: the request used the original (unprefixed) text
    expect(mockEmbeddingsCreate).toHaveBeenCalledWith({
      input: ["short-text"],
      model: "openai/text-embedding-3-large",
      encoding_format: "base64",
    })
    expect(result.embeddings).toHaveLength(1)
    expect(result.embeddings[0]).toEqual([0.10000000149011612, 0.20000000298023224]) // float32 rounding
    spyGetModelQueryPrefix.mockRestore()
  })

})
