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





  __testAugmentVitest_7d8abec966fc.it("update_global_rate_limit_increments_and_get_delay_round_023", async () => {
  	// Load module without additional mocks (use existing suite-level OpenAI mock)
  	const { OpenRouterEmbedder } = await __testAugmentLoadTarget_de59c0146853()
  	const embedder = new OpenRouterEmbedder(mockApiKey)

  	// Access the private static global state for assertions
  	const state = (OpenRouterEmbedder as any).globalRateLimitState
  	// Ensure a clean starting point
  	state.isRateLimited = false
  	state.consecutiveRateLimitErrors = 0
  	state.lastRateLimitError = 0

  	// Simulate two 429 errors in quick succession
  	await (embedder as any).updateGlobalRateLimitState({ status: 429 })
  	const afterFirst = state.consecutiveRateLimitErrors
  	await (embedder as any).updateGlobalRateLimitState({ status: 429 })

  	__testAugmentVitest_7d8abec966fc.expect(afterFirst).toBe(1)
  	__testAugmentVitest_7d8abec966fc.expect(state.consecutiveRateLimitErrors).toBe(2)
  	__testAugmentVitest_7d8abec966fc.expect(state.isRateLimited).toBe(true)

  	// getGlobalRateLimitDelay should return a positive number because rateLimitResetTime is in the future
  	const delay = await (embedder as any).getGlobalRateLimitDelay()
  	__testAugmentVitest_7d8abec966fc.expect(delay).toBeGreaterThan(0)
  })
})

import * as __testAugmentVitest_7d8abec966fc from "vitest";

const __testAugmentLoadTarget_de59c0146853 = async () => {
  __testAugmentVitest_7d8abec966fc.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_7d8abec966fc.vi.resetModules();
  return import("../openrouter.js");
};
