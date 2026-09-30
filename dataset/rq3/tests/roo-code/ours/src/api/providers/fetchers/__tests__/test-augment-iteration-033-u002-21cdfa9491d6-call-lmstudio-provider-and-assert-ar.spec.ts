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

describe("getModels with new GetModelsOptions", () => {
	beforeEach(() => {
		vi.clearAllMocks()
	})





  __testAugmentVitest_77808a204f27.it("calls getLMStudioModels with baseUrl_round_033", async () => {
  	// Mock lmstudio fetcher
  	const mockGetLMStudio = __testAugmentVitest_77808a204f27.vi.fn().mockResolvedValue({
  		"lmstudio/model": { maxTokens: 123, contextWindow: 456, supportsPromptCache: false, description: "lmstudio" },
  	})
  	__testAugmentVitest_77808a204f27.vi.doMock("../lmstudio", () => ({ getLMStudioModels: mockGetLMStudio }))

  	const mod = await __testAugmentLoadTarget_903c4e89ae9e()
  	const { getModels } = mod

  	const res = await getModels({ provider: "lmstudio", baseUrl: "https://lm.test" })

  	// Ensure the lmstudio-specific fetcher was invoked with the baseUrl only
  	__testAugmentVitest_77808a204f27.expect(mockGetLMStudio).toHaveBeenCalledWith("https://lm.test")
  	__testAugmentVitest_77808a204f27.expect(res).toHaveProperty("lmstudio/model")
  })
})



import * as __testAugmentVitest_77808a204f27 from "vitest";

const __testAugmentLoadTarget_903c4e89ae9e = async () => {
  __testAugmentVitest_77808a204f27.vi.doUnmock("../modelCache.js");
  __testAugmentVitest_77808a204f27.vi.resetModules();
  return import("../modelCache.js");
};
