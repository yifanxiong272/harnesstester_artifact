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



	  __testAugmentVitest_4c1bfdc1ad38.it("migrateInvalidApiProvider_handles_update_throw_round_017_pass_03", async () => {
	  	// Mock vscode where globalState.get returns an invalid provider, and update will throw when clearing it
	  	__testAugmentVitest_4c1bfdc1ad38.vi.doMock("vscode", () => ({
	  		Uri: { file: (p: string) => ({ path: p }) },
	  		ExtensionMode: { Development: 1, Production: 2, Test: 3 },
	  	}))

	  	const mockGlobalState = {
	  		get: __testAugmentVitest_4c1bfdc1ad38.vi.fn((key: string) => {
	  			if (key === "apiProvider") return "some-unknown-removed-provider"
	  			return undefined
	  		}),
	  		update: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockImplementation((key: string) => {
	  			if (key === "apiProvider") throw new Error("update-boom")
	  			return Promise.resolve(undefined)
	  		}),
	  	}
	  	const mockSecrets = { get: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined), store: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined), delete: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined) }
	  	const mockContext = { globalState: mockGlobalState, secrets: mockSecrets, extensionUri: { path: "/" }, extensionPath: "/", globalStorageUri: { path: "/" }, logUri: { path: "/" }, extension: {}, extensionMode: 1 }

	  	const module = await __testAugmentLoadTarget_ee215f51855d()
	  	const { ContextProxy } = module

	  	// The update will throw; ensure initialize catches and continues
	  	const proxyLocal = new ContextProxy(mockContext as any)
	  	await proxyLocal.initialize()

	  	// The failing update should have been attempted (we see call)
	  	__testAugmentVitest_4c1bfdc1ad38.expect(mockGlobalState.update).toHaveBeenCalled()

	  	// Initialization should complete regardless
	  	__testAugmentVitest_4c1bfdc1ad38.expect(proxyLocal.isInitialized).toBe(true)
	  })
	})

})

import * as __testAugmentVitest_4c1bfdc1ad38 from "vitest";

const __testAugmentLoadTarget_ee215f51855d = async () => {
  __testAugmentVitest_4c1bfdc1ad38.vi.doUnmock("../ContextProxy.js");
  __testAugmentVitest_4c1bfdc1ad38.vi.resetModules();
  return import("../ContextProxy.js");
};
