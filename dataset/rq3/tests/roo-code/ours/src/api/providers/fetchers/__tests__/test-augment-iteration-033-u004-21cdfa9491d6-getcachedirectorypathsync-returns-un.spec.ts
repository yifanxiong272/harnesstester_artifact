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





  __testAugmentVitest_77808a204f27.it("does not check disk when ContextProxy has no globalStorageUri_round_033", async () => {
  	// Provide a ContextProxy mock lacking globalStorageUri to trigger the undefined path
  	__testAugmentVitest_77808a204f27.vi.doMock("../../../core/config/ContextProxy", () => ({
  		ContextProxy: { instance: {} },
  	}))

  	// Mock fs.existsSync to a spy so we can assert it was not called
  	const fakeFs = {
  		existsSync: __testAugmentVitest_77808a204f27.vi.fn(),
  		readFileSync: __testAugmentVitest_77808a204f27.vi.fn(),
  	}
  	__testAugmentVitest_77808a204f27.vi.doMock("fs", () => fakeFs)

  	const mod = await __testAugmentLoadTarget_903c4e89ae9e()
  	const { getModelsFromCache } = mod

  	// Expect undefined because cache directory cannot be resolved synchronously
  	const result = getModelsFromCache("openrouter")
  	__testAugmentVitest_77808a204f27.expect(result).toBeUndefined()
  	// Disk should NOT be queried when there's no globalStorageUri
  	__testAugmentVitest_77808a204f27.expect(fakeFs.existsSync).not.toHaveBeenCalled()
  })
})



import * as __testAugmentVitest_77808a204f27 from "vitest";

const __testAugmentLoadTarget_903c4e89ae9e = async () => {
  __testAugmentVitest_77808a204f27.vi.doUnmock("../modelCache.js");
  __testAugmentVitest_77808a204f27.vi.resetModules();
  return import("../modelCache.js");
};
