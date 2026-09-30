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





  __testAugmentVitest_7d8abec966fc.it("creates_multiple_batches_when_batch_limit_reached_round_023_pass_03", async () => {
  	// Force small batch token limit to trigger the break and multiple batches
  	__testAugmentVitest_7d8abec966fc.vi.doMock("../../constants", () => ({
  		MAX_BATCH_TOKENS: 2,
  		MAX_ITEM_TOKENS: 1000,
  		MAX_BATCH_RETRIES: 3,
  		INITIAL_RETRY_DELAY_MS: 10,
  	}))

  	const { OpenRouterEmbedder } = await __testAugmentLoadTarget_de59c0146853()
  	const embedder = new OpenRouterEmbedder(mockApiKey)

  	// Prepare two different base64 embeddings for two batches
  	const embA = new Float32Array([1.0])
  	const embB = new Float32Array([2.0])
  	const base64A = Buffer.from(embA.buffer).toString("base64")
  	const base64B = Buffer.from(embB.buffer).toString("base64")

  	// First call returns embedding for first batch (2 items fit), second call returns final item
  	mockEmbeddingsCreate.mockImplementationOnce(() => Promise.resolve({ data: [{ embedding: base64A }, { embedding: base64A }], usage: { prompt_tokens: 2, total_tokens: 2 } }))
  	mockEmbeddingsCreate.mockImplementationOnce(() => Promise.resolve({ data: [{ embedding: base64B }], usage: { prompt_tokens: 1, total_tokens: 1 } }))

  	// Three short texts: each has itemTokens = ceil(length/4) -> using short strings => 1 token each
  	const texts = ["a", "b", "c"]
  	const result = await embedder.createEmbeddings(texts)

  	// Should have been called twice due to MAX_BATCH_TOKENS = 2
  	__testAugmentVitest_7d8abec966fc.expect(mockEmbeddingsCreate).toHaveBeenCalledTimes(2)

  	// Total embeddings should be 3 and usage should accumulate
  	__testAugmentVitest_7d8abec966fc.expect(result.embeddings.length).toBe(3)
  	// Use tolerant numeric comparison for Float32-decoded values
  	__testAugmentVitest_7d8abec966fc.expect(result.embeddings[0][0]).toBeCloseTo(1.0, 4)
  	__testAugmentVitest_7d8abec966fc.expect(result.embeddings[2][0]).toBeCloseTo(2.0, 4)
  	__testAugmentVitest_7d8abec966fc.expect(result.usage.promptTokens).toBe(3)
  })
})

import * as __testAugmentVitest_7d8abec966fc from "vitest";

const __testAugmentLoadTarget_de59c0146853 = async () => {
  __testAugmentVitest_7d8abec966fc.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_7d8abec966fc.vi.resetModules();
  return import("../openrouter.js");
};
