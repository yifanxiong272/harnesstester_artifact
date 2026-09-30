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





  __testAugmentVitest_7d8abec966fc.it("retries_on_429_then_succeeds_round_023_pass_02", async () => {
  	// Make retry delays tiny to speed the test
  	__testAugmentVitest_7d8abec966fc.vi.doMock("../../constants", () => ({
  		MAX_BATCH_TOKENS: 1000,
  		MAX_ITEM_TOKENS: 1000,
  		MAX_BATCH_RETRIES: 3,
  		INITIAL_RETRY_DELAY_MS: 1,
  	}))

  	const { OpenRouterEmbedder } = await __testAugmentLoadTarget_de59c0146853()
  	const embedder = new OpenRouterEmbedder(mockApiKey)

  	// First call rejects with a 429-like HttpError, second call resolves with a valid base64 embedding
  	const testEmbedding = new Float32Array([0.55, 0.66])
  	const base64String = Buffer.from(testEmbedding.buffer).toString("base64")

  	mockEmbeddingsCreate.mockImplementationOnce(() => Promise.reject(Object.assign(new Error("rate limited"), { status: 429 })))
  	mockEmbeddingsCreate.mockImplementationOnce(() => Promise.resolve({ data: [{ embedding: base64String }], usage: { prompt_tokens: 2, total_tokens: 2 } }))

  	// Use fake timers so the internal setTimeout for the retry does not slow the test
  	__testAugmentVitest_7d8abec966fc.vi.useFakeTimers()

  	const promise = embedder.createEmbeddings(["retry-me"])

  	// Advance timers to allow any scheduled retry wait to complete
  	await __testAugmentVitest_7d8abec966fc.vi.runAllTimersAsync()

  	const result = await promise

  	// Restore real timers for other tests
  	__testAugmentVitest_7d8abec966fc.vi.useRealTimers()

  	// Should have retried, so embeddings.create called at least twice
  	__testAugmentVitest_7d8abec966fc.expect(mockEmbeddingsCreate).toHaveBeenCalledTimes(2)
  	// Use tolerant comparisons for Float32-decoded values
  	__testAugmentVitest_7d8abec966fc.expect(result.embeddings[0][0]).toBeCloseTo(0.55, 4)
  	__testAugmentVitest_7d8abec966fc.expect(result.embeddings[0][1]).toBeCloseTo(0.66, 4)
  	__testAugmentVitest_7d8abec966fc.expect(result.usage.promptTokens).toBe(2)
  })
})

import * as __testAugmentVitest_7d8abec966fc from "vitest";

const __testAugmentLoadTarget_de59c0146853 = async () => {
  __testAugmentVitest_7d8abec966fc.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_7d8abec966fc.vi.resetModules();
  return import("../openrouter.js");
};
