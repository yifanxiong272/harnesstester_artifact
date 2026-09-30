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



	  __testAugmentVitest_4c1bfdc1ad38.it("getProviderSettings_removes_legacy_keys_and_sanitizes_provider_round_017_pass_02", async () => {
	  	// Inject a legacy key (claudeCodePath) and an invalid provider via public API
	  	await proxy.setValues({
	  		// legacy key that should be removed by sanitizeProviderValues
	  		claudeCodePath: "/tmp/claude",
	  		// invalid provider should be sanitized away
	  		apiProvider: "some-unknown-removed-provider",
	  		// include a normal provider key to ensure other values flow through
	  		apiModelId: "some-model",
	  	})

	  	const settings = proxy.getProviderSettings()

	  	// Legacy key should not appear on the returned provider settings
	  	__testAugmentVitest_4c1bfdc1ad38.expect((settings as any).claudeCodePath).toBeUndefined()

	  	// Unknown apiProvider should have been sanitized (removed)
	  	__testAugmentVitest_4c1bfdc1ad38.expect(settings.apiProvider).toBeUndefined()

	  	// Other settings should still be present
	  	__testAugmentVitest_4c1bfdc1ad38.expect(settings.apiModelId).toBe("some-model")
	  })
	})

})

import * as __testAugmentVitest_4c1bfdc1ad38 from "vitest";

const __testAugmentLoadTarget_ee215f51855d = async () => {
  __testAugmentVitest_4c1bfdc1ad38.vi.doUnmock("../ContextProxy.js");
  __testAugmentVitest_4c1bfdc1ad38.vi.resetModules();
  return import("../ContextProxy.js");
};
