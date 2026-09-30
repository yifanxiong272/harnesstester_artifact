import type { MockedClass, MockedFunction } from "vitest"
import { describe, it, expect, beforeEach, vi } from "vitest"
import { OpenAI } from "openai"
import { OpenRouterEmbedder, OPENROUTER_DEFAULT_PROVIDER_NAME } from "../openrouter"
import { getModelDimension, getDefaultModelId } from "../../../../shared/embeddingModels"

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





  __testAugmentVitest_7d8abec966fc.it("model_prefix_skipped_if_prefixing_exceeds_token_limit_round_023", async () => {
  	// Force a short MAX_ITEM_TOKENS so adding the prefix will exceed the per-item token limit
  	__testAugmentVitest_7d8abec966fc.vi.doMock("../../constants", () => ({
  		MAX_BATCH_TOKENS: 1000,
  		MAX_ITEM_TOKENS: 1,
  		MAX_BATCH_RETRIES: 3,
  		INITIAL_RETRY_DELAY_MS: 50,
  	}))

  	// Provide a long-enough query prefix so prefixing would increase estimated tokens
  	__testAugmentVitest_7d8abec966fc.vi.doMock("../../../../shared/embeddingModels", () => ({
  		getModelQueryPrefix: (provider: string, model: string) => "LONGPREFIX-",
  		getDefaultModelId: (provider: string) => "openai/text-embedding-3-large",
  		getModelDimension: () => 3,
  	}))

  	const { OpenRouterEmbedder } = await __testAugmentLoadTarget_de59c0146853()
  	const embedder = new OpenRouterEmbedder(mockApiKey)

  	// Prepare a base64 embedding response
  	const testEmbedding = new Float32Array([0.333, 0.666])
  	const base64String = Buffer.from(testEmbedding.buffer).toString("base64")
  	mockEmbeddingsCreate.mockResolvedValue({ data: [{ embedding: base64String }], usage: { prompt_tokens: 1, total_tokens: 1 } })

  	// Short text which when prefixed will exceed the mocked MAX_ITEM_TOKENS
  	const originalText = "a"
  	await embedder.createEmbeddings([originalText])

  	// Because prefixing would exceed the item token limit, the implementation should call the API with the original text
  	__testAugmentVitest_7d8abec966fc.expect(mockEmbeddingsCreate).toHaveBeenCalledWith({
  		input: [originalText],
  		model: "openai/text-embedding-3-large",
  		encoding_format: "base64",
  	})
  })
})

import * as __testAugmentVitest_7d8abec966fc from "vitest";

const __testAugmentLoadTarget_de59c0146853 = async () => {
  __testAugmentVitest_7d8abec966fc.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_7d8abec966fc.vi.resetModules();
  return import("../openrouter.js");
};
