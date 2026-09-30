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



	  __testAugmentVitest_4c1bfdc1ad38.it("migrateImageGenerationSettings_stores_secret_when_missing_round_017_pass_03", async () => {
	  	// Per-test mock of vscode to control globalState and secrets during module load
	  	__testAugmentVitest_4c1bfdc1ad38.vi.doMock("vscode", () => ({
	  		Uri: { file: (path: string) => ({ path }) },
	  		ExtensionMode: { Development: 1, Production: 2, Test: 3 },
	  	}))

	  	// Provide an ExtensionContext where secrets.get returns undefined (so migration will store)
	  	const mockGlobalState = {
	  		get: __testAugmentVitest_4c1bfdc1ad38.vi.fn((key: string) => {
	  			if (key === "openRouterImageGenerationSettings") return { openRouterApiKey: "migrated-key", selectedModel: "migrated-model" }
	  			return undefined
	  		}),
	  		update: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined),
	  	}
	  	const mockSecrets = {
	  		get: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined), // no existing secret
	  		store: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined),
	  		delete: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined),
	  	}
	  	const mockContext = {
	  		globalState: mockGlobalState,
	  		secrets: mockSecrets,
	  		extensionUri: { path: "/x" },
	  		extensionPath: "/x",
	  		globalStorageUri: { path: "/y" },
	  		logUri: { path: "/z" },
	  		extension: { packageJSON: {} },
	  		extensionMode: 1,
	  	}

	  	// Load the target module fresh so our per-test mocks are used
	  	const module = await __testAugmentLoadTarget_ee215f51855d()
	  	const { ContextProxy } = module

	  	const proxyLocal = new ContextProxy(mockContext as any)
	  	await proxyLocal.initialize()

	  	// Should have stored the migrated openRouterImageApiKey into secrets
	  	__testAugmentVitest_4c1bfdc1ad38.expect(mockSecrets.store).toHaveBeenCalledWith("openRouterImageApiKey", "migrated-key")

	  	// Should have migrated the selected model into global state
	  	__testAugmentVitest_4c1bfdc1ad38.expect(mockGlobalState.update).toHaveBeenCalledWith(
	  		"openRouterImageGenerationSelectedModel",
	  		"migrated-model",
	  	)

	  	// Should have cleaned up the old nested settings
	  	__testAugmentVitest_4c1bfdc1ad38.expect(mockGlobalState.update).toHaveBeenCalledWith("openRouterImageGenerationSettings", undefined)

	  	// Cache should reflect the migrated secret
	  	__testAugmentVitest_4c1bfdc1ad38.expect(proxyLocal.getSecret("openRouterImageApiKey")).toBe("migrated-key")
	  })
	})

})

import * as __testAugmentVitest_4c1bfdc1ad38 from "vitest";

const __testAugmentLoadTarget_ee215f51855d = async () => {
  __testAugmentVitest_4c1bfdc1ad38.vi.doUnmock("../ContextProxy.js");
  __testAugmentVitest_4c1bfdc1ad38.vi.resetModules();
  return import("../ContextProxy.js");
};
