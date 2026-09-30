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



describe("empty cache protection", () => {
	let mockCache: any
	let mockGet: Mock
	let mockSet: Mock

	beforeEach(() => {
		vi.clearAllMocks()
		// Get the mock cache instance
		const MockedNodeCache = vi.mocked(NodeCache)
		mockCache = new MockedNodeCache()
		mockGet = mockCache.get
		mockSet = mockCache.set
		// Reset memory cache to always miss by default
		mockGet.mockReturnValue(undefined)
	})


  __testAugmentVitest_77808a204f27.it("getModels_handles_safeWriteJson_failure_round_033_pass_03", async () => {
  	// Mock safeWriteJson to reject to exercise the writeModels catch branch inside getModels
  	__testAugmentVitest_77808a204f27.vi.doMock("../../../../utils/safeWriteJson", () => ({
  		safeWriteJson: __testAugmentVitest_77808a204f27.vi.fn().mockRejectedValue(new Error("disk write failed")),
  	}))
  	// Provide a valid cache directory path so writeModels attempts to write
  	__testAugmentVitest_77808a204f27.vi.doMock("../../../../utils/storage", () => ({ getCacheDirectoryPath: async () => "/mock/cache" }))

  	// Mock the openrouter provider to return a non-empty model set so writeModels is invoked
  	const mockModels = {
  		"openrouter/x": { maxTokens: 10, contextWindow: 20, supportsPromptCache: false, description: "x" },
  	}
  	__testAugmentVitest_77808a204f27.vi.doMock("../openrouter", () => ({ getOpenRouterModels: __testAugmentVitest_77808a204f27.vi.fn().mockResolvedValue(mockModels) }))

  	// Spy on console.error to confirm the write error is logged
  	const consoleSpy = __testAugmentVitest_77808a204f27.vi.spyOn(console, "error").mockImplementation(() => {})

  	// Load target after mocks
  	const mod = await __testAugmentLoadTarget_903c4e89ae9e()
  	const { getModels } = mod

  	const res = await getModels({ provider: "openrouter" })

  	__testAugmentVitest_77808a204f27.expect(res).toEqual(mockModels)
  	// safeWriteJson failed but getModels should still return models and log the error
  	__testAugmentVitest_77808a204f27.expect(consoleSpy).toHaveBeenCalled()

  	consoleSpy.mockRestore()
  })
})

import * as __testAugmentVitest_77808a204f27 from "vitest";

const __testAugmentLoadTarget_903c4e89ae9e = async () => {
  __testAugmentVitest_77808a204f27.vi.doUnmock("../modelCache.js");
  __testAugmentVitest_77808a204f27.vi.resetModules();
  return import("../modelCache.js");
};
