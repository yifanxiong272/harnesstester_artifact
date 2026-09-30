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





  __testAugmentVitest_7d8abec966fc.it("formats_and_throws_on_non_429_errors_round_023_pass_03", async () => {
  	// Mock validation helpers' formatEmbeddingError so we can assert it was used
  	__testAugmentVitest_7d8abec966fc.vi.doMock("../../shared/validation-helpers", () => ({
  		withValidationErrorHandling: (fn: any, provider?: string) => fn,
  		formatEmbeddingError: (err: any, retries: number) => new Error(`formatted:${err.message}:${retries}`),
  		HttpError: class extends Error {},
  	}))

  	const { OpenRouterEmbedder } = await __testAugmentLoadTarget_de59c0146853()
  	const embedder = new OpenRouterEmbedder(mockApiKey)

  	// Make the embeddings.create reject with a generic (non-429) error
  	mockEmbeddingsCreate.mockRejectedValueOnce(new Error("unexpected-failure"))

  	await __testAugmentVitest_7d8abec966fc.expect(embedder.createEmbeddings(["x"]))
  		.rejects.toThrow("formatted:unexpected-failure:3")
  })
})

import * as __testAugmentVitest_7d8abec966fc from "vitest";

const __testAugmentLoadTarget_de59c0146853 = async () => {
  __testAugmentVitest_7d8abec966fc.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_7d8abec966fc.vi.resetModules();
  return import("../openrouter.js");
};
