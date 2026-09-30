// Mocks must come first, before imports

// Mock NodeCache to allow controlling cache behavior
vi.mock("node-cache", () => {
	const mockGet = vi.fn().mockReturnValue(undefined)
	const mockSet = vi.fn()
	const mockDel = vi.fn()

	return {
		default: vi.fn().mockImplementation(() => ({
			get: mockGet,
			set: mockSet,
			del: mockDel,
		})),
	}
})

// Mock fs/promises to avoid file system operations
vi.mock("fs/promises", () => ({
	writeFile: vi.fn().mockResolvedValue(undefined),
	readFile: vi.fn().mockResolvedValue("{}"),
	mkdir: vi.fn().mockResolvedValue(undefined),
}))

// Mock fs (synchronous) for disk cache fallback
vi.mock("fs", () => ({
	existsSync: vi.fn().mockReturnValue(false),
	readFileSync: vi.fn().mockReturnValue("{}"),
}))

// Mock all the model fetchers
vi.mock("../litellm")
vi.mock("../openrouter")
vi.mock("../requesty")

// Mock ContextProxy with a simple static instance
vi.mock("../../../core/config/ContextProxy", () => ({
	ContextProxy: {
		instance: {
			globalStorageUri: {
				fsPath: "/mock/storage/path",
			},
		},
	},
}))

// Then imports
import type { Mock } from "vitest"
import * as fsSync from "fs"
import NodeCache from "node-cache"
import { getModels, getModelsFromCache } from "../modelCache"
import { getLiteLLMModels } from "../litellm"
import { getOpenRouterModels } from "../openrouter"
import { getRequestyModels } from "../requesty"

const mockGetLiteLLMModels = getLiteLLMModels as Mock<typeof getLiteLLMModels>
const mockGetOpenRouterModels = getOpenRouterModels as Mock<typeof getOpenRouterModels>
const mockGetRequestyModels = getRequestyModels as Mock<typeof getRequestyModels>

const DUMMY_REQUESTY_KEY = "requesty-key-for-testing"


describe("getModelsFromCache disk fallback", () => {
	let mockCache: any

	beforeEach(() => {
		vi.clearAllMocks()
		// Get the mock cache instance
		const MockedNodeCache = vi.mocked(NodeCache)
		mockCache = new MockedNodeCache()
		// Reset memory cache to always miss
		mockCache.get.mockReturnValue(undefined)
		// Reset fs mocks
		vi.mocked(fsSync.existsSync).mockReturnValue(false)
		vi.mocked(fsSync.readFileSync).mockReturnValue("{}")
	})





  __testAugmentVitest_77808a204f27.it("poe_provider_calls_getPoeModels_round_033_pass_02", async () => {
  	// Mock the poe fetcher to observe its arguments
  	const mockGetPoe = __testAugmentVitest_77808a204f27.vi.fn().mockResolvedValue({
  		"poe/model": { maxTokens: 7, contextWindow: 14, supportsPromptCache: false, description: "poe" },
  	})
  	__testAugmentVitest_77808a204f27.vi.doMock("../poe", () => ({ getPoeModels: mockGetPoe }))

  	const mod = await __testAugmentLoadTarget_903c4e89ae9e()
  	const { getModels } = mod

  	const apiKey = "poe-key"
  	const baseUrl = "https://poe.test"
  	const res = await getModels({ provider: "poe", apiKey, baseUrl })

  	// The poe fetcher should be called with (apiKey, baseUrl)
  	__testAugmentVitest_77808a204f27.expect(mockGetPoe).toHaveBeenCalledWith(apiKey, baseUrl)
  	__testAugmentVitest_77808a204f27.expect(res).toHaveProperty("poe/model")
  })
})


import * as __testAugmentVitest_77808a204f27 from "vitest";

const __testAugmentLoadTarget_903c4e89ae9e = async () => {
  __testAugmentVitest_77808a204f27.vi.doUnmock("../modelCache.js");
  __testAugmentVitest_77808a204f27.vi.resetModules();
  return import("../modelCache.js");
};
