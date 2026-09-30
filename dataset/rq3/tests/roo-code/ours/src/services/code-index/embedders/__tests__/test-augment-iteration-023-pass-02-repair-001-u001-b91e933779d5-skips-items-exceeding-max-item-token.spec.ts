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





  __testAugmentVitest_7d8abec966fc.it("skips_items_exceeding_max_item_tokens_round_023_pass_02", async () => {
  	const { OpenRouterEmbedder } = await __testAugmentLoadTarget_de59c0146853()
  	// Create embedder with a very small per-item token limit so some items are skipped
  	const embedder = new OpenRouterEmbedder(mockApiKey, undefined, 1)

  	// Prepare a response for the short item only
  	const shortEmbedding = new Float32Array([0.42])
  	const base64String = Buffer.from(shortEmbedding.buffer).toString("base64")
  	mockEmbeddingsCreate.mockResolvedValue({ data: [{ embedding: base64String }], usage: { prompt_tokens: 1, total_tokens: 1 } })

  	// Long text will exceed per-item tokens (length -> ceil(length/4) > 1) and should be skipped
  	const longText = "xxxxxxxxxxxx" // length 12 => ceil(12/4)=3 > 1
  	const shortText = "a" // length 1 => ceil(1/4)=1 <= 1

  	const result = await embedder.createEmbeddings([longText, shortText])

  	// Expect the API to be called only with the short text (the long one is skipped)
  	__testAugmentVitest_7d8abec966fc.expect(mockEmbeddingsCreate).toHaveBeenCalledWith({
  		input: [shortText],
  		model: "openai/text-embedding-3-large",
  		encoding_format: "base64",
  	})

  	// A warning should have been emitted for the skipped item
  	__testAugmentVitest_7d8abec966fc.expect(console.warn).toHaveBeenCalled()

  	// Verify that returned embeddings correspond to the provided embedding for the short item
  	__testAugmentVitest_7d8abec966fc.expect(result.embeddings.length).toBe(1)
  	// Use tolerant comparison because embedding values are Float32-decoded and may have small rounding differences
  	__testAugmentVitest_7d8abec966fc.expect(result.embeddings[0][0]).toBeCloseTo(0.42, 4)
  })
})

import * as __testAugmentVitest_7d8abec966fc from "vitest";

const __testAugmentLoadTarget_de59c0146853 = async () => {
  __testAugmentVitest_7d8abec966fc.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_7d8abec966fc.vi.resetModules();
  return import("../openrouter.js");
};
