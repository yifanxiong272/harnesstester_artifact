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



	  __testAugmentVitest_4c1bfdc1ad38.it("migrate legacy condensing prompt preserves existing CONDENSE -> _round_017", async () => {
	  	// Ensure clean mocks for this scenario
	  	__testAugmentVitest_4c1bfdc1ad38.vi.clearAllMocks()

	  	// Legacy prompt is present, but customSupportPrompts already contains a CONDENSE value
	  	mockGlobalState.get.mockImplementation((key) => {
	  		if (key === "customCondensingPrompt") return "legacy prompt that should be removed"
	  		if (key === "customSupportPrompts") return { CONDENSE: "existing-new-prompt", EXPLAIN: "x" }
	  		return undefined
	  	})

	  	const proxyLocal = new ContextProxy(mockContext)
	  	await proxyLocal.initialize()

	  	// The migration should NOT overwrite existing customSupportPrompts.CONDENSE
	  	const updateCalls = mockGlobalState.update.mock.calls
	  	const customSupportCalls = updateCalls.filter((c) => c[0] === "customSupportPrompts")
	  	__testAugmentVitest_4c1bfdc1ad38.expect(customSupportCalls.length).toBe(0)

	  	// The legacy field itself should be removed
	  	__testAugmentVitest_4c1bfdc1ad38.expect(mockGlobalState.update).toHaveBeenCalledWith("customCondensingPrompt", undefined)

	  	// The preserved prompts should remain retrievable from cache
	  	__testAugmentVitest_4c1bfdc1ad38.expect(proxyLocal.getGlobalState("customSupportPrompts")).toEqual({ CONDENSE: "existing-new-prompt", EXPLAIN: "x" })
	  })
	})

})

import * as __testAugmentVitest_4c1bfdc1ad38 from "vitest";

const __testAugmentLoadTarget_ee215f51855d = async () => {
  __testAugmentVitest_4c1bfdc1ad38.vi.doUnmock("../ContextProxy.js");
  __testAugmentVitest_4c1bfdc1ad38.vi.resetModules();
  return import("../ContextProxy.js");
};
