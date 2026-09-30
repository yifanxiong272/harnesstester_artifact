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





  __testAugmentVitest_7d8abec966fc.it("constructor_handles_openai_ctor_error_round_023_pass_02", async () => {
  	// Make OpenAI constructor throw to exercise the constructor catch path and ensure handleOpenAIError is used
  	__testAugmentVitest_7d8abec966fc.vi.doMock("openai", () => ({
  		OpenAI: class {
  			constructor() {
  				throw new Error("ByteString conversion failure")
  			}
  		},
  	}))

  	// Provide a deterministic handler that produces a recognizable Error to be thrown by the embedder
  	__testAugmentVitest_7d8abec966fc.vi.doMock("../../../../api/providers/utils/openai-error-handler", () => ({
  		handleOpenAIError: (err: any, provider: string) => new Error(`handled-${provider}-error`),
  	}))

  	const { OpenRouterEmbedder } = await __testAugmentLoadTarget_de59c0146853()

  	__testAugmentVitest_7d8abec966fc.expect(() => new OpenRouterEmbedder("irrelevant-key")).toThrow("handled-OpenRouter-error")
  })
})

import * as __testAugmentVitest_7d8abec966fc from "vitest";

const __testAugmentLoadTarget_de59c0146853 = async () => {
  __testAugmentVitest_7d8abec966fc.vi.doUnmock("../openrouter.js");
  __testAugmentVitest_7d8abec966fc.vi.resetModules();
  return import("../openrouter.js");
};
