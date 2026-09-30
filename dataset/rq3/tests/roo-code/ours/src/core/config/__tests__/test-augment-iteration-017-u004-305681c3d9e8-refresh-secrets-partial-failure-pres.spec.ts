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



	  __testAugmentVitest_4c1bfdc1ad38.it("refreshSecrets preserves previous value when a secret read fails and updates others -> _round_017", async () => {
	  	// Use the proxy instance from the suite-level beforeEach which was initialized with mockSecrets.get returning "test-secret".
	  	// Now make secrets.get throw for the first secret key and succeed for others.
	  	const failingKey = SECRET_STATE_KEYS[0]

	  	mockSecrets.get.mockImplementation(async (key) => {
	  		if (key === failingKey) throw new Error("read-failure")
	  		return "refreshed-" + String(key)
	  	})

	  	// Ensure we have the original cached value for failingKey from initialization
	  	__testAugmentVitest_4c1bfdc1ad38.expect(proxy.getSecret(failingKey)).toBe("test-secret")

	  	await proxy.refreshSecrets()

	  	// The failing key should retain its previous cache value (the error branch does not clear cache)
	  	__testAugmentVitest_4c1bfdc1ad38.expect(proxy.getSecret(failingKey)).toBe("test-secret")

	  	// Other secret keys should have been refreshed
	  	const otherKey = SECRET_STATE_KEYS.find((k) => k !== failingKey) as string
	  	__testAugmentVitest_4c1bfdc1ad38.expect(proxy.getSecret(otherKey)).toBe("refreshed-" + otherKey)
	  })
	})

})

import * as __testAugmentVitest_4c1bfdc1ad38 from "vitest";

const __testAugmentLoadTarget_ee215f51855d = async () => {
  __testAugmentVitest_4c1bfdc1ad38.vi.doUnmock("../ContextProxy.js");
  __testAugmentVitest_4c1bfdc1ad38.vi.resetModules();
  return import("../ContextProxy.js");
};
