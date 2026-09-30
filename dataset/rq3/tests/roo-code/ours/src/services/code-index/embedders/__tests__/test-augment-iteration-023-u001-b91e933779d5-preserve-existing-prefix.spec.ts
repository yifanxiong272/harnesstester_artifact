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





  __testAugmentVitest_7d8abec966fc.it("model_prefix_preserves_existing_prefix_round_023", async () => {
  	// Ensure model query prefix is present so we can exercise the "already prefixed" branch
  	__testAugmentVitest_7d8abec966fc.vi.doMock("../../../../shared/embeddingModels", () => ({
  		getModelQueryPrefix: (provider: string, model: string) => "PREFIX:",
  		getDefaultModelId: (provider: string) => "openai/text-embedding-3-large",
  		getModelDimension: () => 3,
  	}))

  	const { OpenRouterEmbedder } = await __testAugmentLoadTarget_de59c0146853()

  	// Use the suite-level mockApiKey and mockEmbeddingsCreate declared in the seed harness
  	const embedder = new OpenRouterEmbedder(mockApiKey)

  	// Prepare a base64 embedding response
  	const testEmbedding = new Float32Array([0.125, 0.25, 0.5])
  	const base64String = Buffer.from(testEmbedding.buffer).toString("base64")
  	mockEmbeddingsCreate.mockResolvedValue({
  		data: [{ embedding: base64String }],
  		usage: { prompt_tokens: 1, total_tokens: 1 },
  	})

  	// Provide a text that already begins with the prefix -> should not be double-prefixed
  	const inputText = "PREFIX:already prefixed text"
  	const result = await embedder.createEmbeddings([inputText])

  	__testAugmentVitest_7d8abec966fc.expect(mockEmbeddingsCreate).toHaveBeenCalledWith({
  		input: [inputText],
  		model: "openai/text-embedding-3-large",
  		encoding_format: "base64",
  	})

  	// The returned embedding should match the decoded Float32Array
  	__testAugmentVitest_7d8abec966fc.expect(result.embeddings[0]).toEqual(Array.from(testEmbedding))
  })
})

import * as __testAugmentVitest_7d8abec966fc from "vitest";

const __testAugmentLoadTarget_de59c0146853 = async () => {
  __testAugmentVitest_7d8abec966fc.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_7d8abec966fc.vi.resetModules();
  return import("../openrouter.js");
};
