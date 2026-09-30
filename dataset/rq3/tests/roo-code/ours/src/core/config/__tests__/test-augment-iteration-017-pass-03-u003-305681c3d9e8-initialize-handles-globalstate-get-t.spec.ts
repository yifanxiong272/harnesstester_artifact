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



	  __testAugmentVitest_4c1bfdc1ad38.it("initialize_handles_globalState_get_throw_round_017_pass_03", async () => {
	  	// Simulate a globalState.get throwing for one key during initialization
	  	__testAugmentVitest_4c1bfdc1ad38.vi.doMock("vscode", () => ({
	  		Uri: { file: (p: string) => ({ path: p }) },
	  		ExtensionMode: { Development: 1, Production: 2, Test: 3 },
	  	}))

	  	const erroringKey = "apiProvider"
	  	const mockGlobalState = {
	  		get: __testAugmentVitest_4c1bfdc1ad38.vi.fn((key: string) => {
	  			if (key === erroringKey) throw new Error("boom-get")
	  			return undefined
	  		}),
	  		update: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined),
	  	}
	  	const mockSecrets = { get: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined), store: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined), delete: __testAugmentVitest_4c1bfdc1ad38.vi.fn().mockResolvedValue(undefined) }
	  	const mockContext = { globalState: mockGlobalState, secrets: mockSecrets, extensionUri: { path: "/" }, extensionPath: "/", globalStorageUri: { path: "/" }, logUri: { path: "/" }, extension: {}, extensionMode: 1 }

	  	const module = await __testAugmentLoadTarget_ee215f51855d()
	  	const { ContextProxy } = module

	  	const proxyLocal = new ContextProxy(mockContext as any)
	  	// Should not throw despite the error during get
	  	await proxyLocal.initialize()

	  	// After initialization, __isInitialized should be true
	  	__testAugmentVitest_4c1bfdc1ad38.expect(proxyLocal.isInitialized).toBe(true)

	  	// The stateCache for the erroring key should be undefined (initial assignment skipped)
	  	__testAugmentVitest_4c1bfdc1ad38.expect(proxyLocal.getGlobalState(erroringKey as any)).toBeUndefined()
	  })
	})

})

import * as __testAugmentVitest_4c1bfdc1ad38 from "vitest";

const __testAugmentLoadTarget_ee215f51855d = async () => {
  __testAugmentVitest_4c1bfdc1ad38.vi.doUnmock("../ContextProxy.js");
  __testAugmentVitest_4c1bfdc1ad38.vi.resetModules();
  return import("../ContextProxy.js");
};
