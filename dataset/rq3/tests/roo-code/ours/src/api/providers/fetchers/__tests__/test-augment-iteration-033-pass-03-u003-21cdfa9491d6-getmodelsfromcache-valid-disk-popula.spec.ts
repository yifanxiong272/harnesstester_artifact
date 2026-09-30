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


  __testAugmentVitest_77808a204f27.it("getModelsFromCache_valid_disk_populates_memory_round_033_pass_03", async () => {
  	// Simulate a valid disk JSON and a present cache directory
  	const diskModels = {
  		"disk/model": { maxTokens: 33, contextWindow: 66, supportsPromptCache: false, description: "disk" },
  	}
  	const fakeFs = {
  		existsSync: __testAugmentVitest_77808a204f27.vi.fn().mockReturnValue(true),
  		readFileSync: __testAugmentVitest_77808a204f27.vi.fn().mockReturnValue(JSON.stringify(diskModels)),
  	}
  	__testAugmentVitest_77808a204f27.vi.doMock("fs", () => fakeFs)

  	// Ensure getCacheDirectoryPathSync sees a global storage path by mocking ContextProxy
  	__testAugmentVitest_77808a204f27.vi.doMock("../../../../core/config/ContextProxy", () => ({
  		ContextProxy: { instance: { globalStorageUri: { fsPath: "/some/storage" } } },
  	}))

  	// Observe NodeCache instance set calls
  	const MockedNodeCache = __testAugmentVitest_77808a204f27.vi.mocked(NodeCache)
  	const mockInstance: any = new MockedNodeCache()
  	mockInstance.set.mockClear()

  	const mod = await __testAugmentLoadTarget_903c4e89ae9e()
  	const { getModelsFromCache } = mod

  	const res = getModelsFromCache("openrouter")
  	__testAugmentVitest_77808a204f27.expect(res).toEqual(diskModels)
  	// Memory cache should be populated with validated data
  	__testAugmentVitest_77808a204f27.expect(mockInstance.set).toHaveBeenCalledWith("openrouter", diskModels)
  })
})

import * as __testAugmentVitest_77808a204f27 from "vitest";

const __testAugmentLoadTarget_903c4e89ae9e = async () => {
  __testAugmentVitest_77808a204f27.vi.doUnmock("../modelCache.js");
  __testAugmentVitest_77808a204f27.vi.resetModules();
  return import("../modelCache.js");
};
