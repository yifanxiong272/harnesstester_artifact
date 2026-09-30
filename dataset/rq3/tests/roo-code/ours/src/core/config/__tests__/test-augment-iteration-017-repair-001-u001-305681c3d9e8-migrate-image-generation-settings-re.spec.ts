// npx vitest core/config/__tests__/ContextProxy.spec.ts

import * as vscode from "vscode"

import { GLOBAL_STATE_KEYS, SECRET_STATE_KEYS, GLOBAL_SECRET_KEYS } from "@roo-code/types"

import { ContextProxy } from "../ContextProxy"

vi.mock("vscode", () => ({
	Uri: {
		file: vi.fn((path) => ({ path })),
	},
	ExtensionMode: {
		Development: 1,
		Production: 2,
		Test: 3,
	},
}))

describe("ContextProxy", () => {
	let proxy: ContextProxy
	let mockContext: any
	let mockGlobalState: any
	let mockSecrets: any

	beforeEach(async () => {
		// Reset mocks
		vi.clearAllMocks()

		// Mock globalState
		mockGlobalState = {
			get: vi.fn(),
			update: vi.fn().mockResolvedValue(undefined),
		}

		// Mock secrets
		mockSecrets = {
			get: vi.fn().mockResolvedValue("test-secret"),
			store: vi.fn().mockResolvedValue(undefined),
			delete: vi.fn().mockResolvedValue(undefined),
		}

		// Mock the extension context
		mockContext = {
			globalState: mockGlobalState,
			secrets: mockSecrets,
			extensionUri: { path: "/test/extension" },
			extensionPath: "/test/extension",
			globalStorageUri: { path: "/test/storage" },
			logUri: { path: "/test/logs" },
			extension: { packageJSON: { version: "1.0.0" } },
			extensionMode: vscode.ExtensionMode.Development,
		}

		// Create proxy instance
		proxy = new ContextProxy(mockContext)
		await proxy.initialize()
	})












	describe("getProviderSettings", () => {



	  __testAugmentVitest_4c1bfdc1ad38.it("migrate old nested openRouterImageGenerationSettings respects existing secret and migrates model -> _round_017", async () => {
	  	// Do NOT clear existing mocks so the suite-level beforeEach mockSecrets.get (which returns "test-secret") remains

	  	// Arrange: make globalState return an old nested settings object
	  	mockGlobalState.get.mockImplementation((key) => {
	  		if (key === "openRouterImageGenerationSettings") {
	  			return { openRouterApiKey: "old-key-123", selectedModel: "openrouter-model-x" }
	  		}
	  		return undefined
	  	})

	  	// Act: create a fresh proxy and initialize (will run migrations)
	  	const proxyLocal = new ContextProxy(mockContext)
	  	await proxyLocal.initialize()

	  	// Assert: Because the suite-level initialization already populated secretCache with a value,
	  	// the migration should NOT call secrets.store for openRouterImageApiKey
	  	__testAugmentVitest_4c1bfdc1ad38.expect(mockSecrets.store).not.toHaveBeenCalled()

	  	// The selected model migration should still occur
	  	__testAugmentVitest_4c1bfdc1ad38.expect(mockGlobalState.update).toHaveBeenCalledWith(
	  		"openRouterImageGenerationSelectedModel",
	  		"openrouter-model-x",
	  	)

	  	// The old nested settings should be cleaned up
	  	__testAugmentVitest_4c1bfdc1ad38.expect(mockGlobalState.update).toHaveBeenCalledWith("openRouterImageGenerationSettings", undefined)

	  	// The proxy should still expose the pre-existing secret value from cache
	  	__testAugmentVitest_4c1bfdc1ad38.expect(proxyLocal.getSecret("openRouterImageApiKey")).toBe("test-secret")
	  })
	})

})

import * as __testAugmentVitest_4c1bfdc1ad38 from "vitest";

const __testAugmentLoadTarget_ee215f51855d = async () => {
  __testAugmentVitest_4c1bfdc1ad38.vi.doUnmock("../ContextProxy.js");
  __testAugmentVitest_4c1bfdc1ad38.vi.resetModules();
  return import("../ContextProxy.js");
};
