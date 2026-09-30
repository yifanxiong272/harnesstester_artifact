import type { MockedFunction } from "vitest"

import { CodeIndexOllamaEmbedder } from "../ollama"

// Mock fetch
global.fetch = vitest.fn() as MockedFunction<typeof fetch>

// Mock i18n
vitest.mock("../../../../i18n", () => ({
	t: (key: string, params?: Record<string, any>) => {
		const translations: Record<string, string> = {
			"embeddings:validation.serviceUnavailable":
				"The embedder service is not available. Please ensure it is running and accessible.",
			"embeddings:validation.modelNotAvailable":
				"The specified model is not available. Please check your model configuration.",
			"embeddings:validation.connectionFailed":
				"Failed to connect to the embedder service. Please check your connection settings and ensure the service is running.",
			"embeddings:validation.configurationError": "Invalid embedder configuration. Please review your settings.",
			"embeddings:errors.ollama.serviceNotRunning":
				"Ollama service is not running at {{baseUrl}}. Please start Ollama first.",
			"embeddings:errors.ollama.serviceUnavailable":
				"Ollama service is unavailable at {{baseUrl}}. HTTP status: {{status}}",
			"embeddings:errors.ollama.modelNotFound":
				"Model '{{model}}' not found. Available models: {{availableModels}}",
			"embeddings:errors.ollama.modelNotEmbedding": "Model '{{model}}' is not embedding capable",
			"embeddings:errors.ollama.hostNotFound": "Ollama host not found: {{baseUrl}}",
			"embeddings:errors.ollama.connectionTimeout": "Connection to Ollama timed out at {{baseUrl}}",
		}
		// Handle parameter substitution
		let result = translations[key] || key
		if (params) {
			Object.entries(params).forEach(([param, value]) => {
				result = result.replace(new RegExp(`{{${param}}}`, "g"), String(value))
			})
		}
		return result
	},
}))

// Mock console methods
const consoleMocks = {
	error: vitest.spyOn(console, "error").mockImplementation(() => {}),
}

describe("CodeIndexOllamaEmbedder", () => {
	let embedder: CodeIndexOllamaEmbedder
	let mockFetch: MockedFunction<typeof fetch>

	beforeEach(() => {
		vitest.clearAllMocks()
		consoleMocks.error.mockClear()

		mockFetch = global.fetch as MockedFunction<typeof fetch>

		embedder = new CodeIndexOllamaEmbedder({
			ollamaModelId: "nomic-embed-text",
			ollamaBaseUrl: "http://localhost:11434",
		})
	})

	afterEach(() => {
		vitest.clearAllMocks()
	})


  __testAugmentVitest_af2b4a5d6087.it("createEmbeddings preserves existing prefix and adds to others_round_032", async () => {
  	// Make the provider return a prefix string so the prefixing branch is used
  	__testAugmentVitest_af2b4a5d6087.vi.doMock("../../../../shared/embeddingModels", () => ({
  		getModelQueryPrefix: (provider: string, model: string) => "PREF:",
  	}))

  	const mod = await __testAugmentLoadTarget_1ea93019718b()
  	const { CodeIndexOllamaEmbedder } = mod as any

  	const mockFetch = global.fetch as any
  	mockFetch.mockImplementationOnce(() =>
  		Promise.resolve({
  			ok: true,
  			status: 200,
  			json: () => Promise.resolve({ embeddings: [[0.9]] }),
  		} as Response),
  	)

  	const embedder = new CodeIndexOllamaEmbedder({ ollamaBaseUrl: "http://localhost:11434", ollamaModelId: "nomic-embed-text" })

  	// One text already contains the prefix, the other does not
  	await embedder.createEmbeddings(["PREF:already", "needs"])

  	__testAugmentVitest_af2b4a5d6087.expect(mockFetch).toHaveBeenCalled()
  	const call = mockFetch.mock.calls[0]
  	const body = JSON.parse(call[1].body)
  	// Expect that the first item was not double-prefixed and the second was prefixed
  	__testAugmentVitest_af2b4a5d6087.expect(body.input).toEqual(["PREF:already", "PREF:needs"])
  })
})

import * as __testAugmentVitest_af2b4a5d6087 from "vitest";

const __testAugmentLoadTarget_1ea93019718b = async () => {
  __testAugmentVitest_af2b4a5d6087.vi.doUnmock("../ollama.js");
  __testAugmentVitest_af2b4a5d6087.vi.resetModules();
  return import("../ollama.js");
};
