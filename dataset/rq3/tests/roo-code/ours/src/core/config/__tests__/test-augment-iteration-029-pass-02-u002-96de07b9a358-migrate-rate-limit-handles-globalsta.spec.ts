// npx vitest src/core/config/__tests__/ProviderSettingsManager.spec.ts

import { ExtensionContext } from "vscode"

import type { ProviderSettings } from "@roo-code/types"

import { ProviderSettingsManager, ProviderProfiles } from "../ProviderSettingsManager"

// Mock VSCode ExtensionContext
const mockSecrets = {
	get: vi.fn(),
	store: vi.fn(),
	delete: vi.fn(),
}

const mockGlobalState = {
	get: vi.fn(),
	update: vi.fn(),
}

const mockContext = {
	secrets: mockSecrets,
	globalState: mockGlobalState,
} as unknown as ExtensionContext

describe("ProviderSettingsManager", () => {
	let providerSettingsManager: ProviderSettingsManager

	beforeEach(() => {
		vi.clearAllMocks()
		// Reset all mock implementations to default successful behavior
		mockSecrets.get.mockResolvedValue(null)
		mockSecrets.store.mockResolvedValue(undefined)
		mockSecrets.delete.mockResolvedValue(undefined)
		mockGlobalState.get.mockReturnValue(undefined)
		mockGlobalState.update.mockResolvedValue(undefined)

		providerSettingsManager = new ProviderSettingsManager(mockContext)
	})








  __testAugmentVitest_5c718f26a041.it("migrate_rate_limit_handles_globalstate_error_round_029_pass_02", async () => {
  	// Arrange: simulate globalState.get throwing and a profile that needs rate limit migration
  	mockGlobalState.get.mockImplementationOnce(() => {
  		throw new Error("global state error")
  	})

  	mockSecrets.get.mockResolvedValueOnce(
  		JSON.stringify({
  			currentApiConfigName: "default",
  			apiConfigs: {
  				default: { id: "default", rateLimitSeconds: undefined },
  				test: { apiProvider: "anthropic", id: "t1", rateLimitSeconds: undefined },
  			},
  			migrations: { rateLimitSecondsMigrated: false },
  		}),
  	)

  	// Act
  	await providerSettingsManager.initialize()

  	// Assert: even though globalState.get threw, rateLimitSeconds should default to 0
  	const calls = mockSecrets.store.mock.calls
  	__testAugmentVitest_5c718f26a041.expect(calls.length).toBeGreaterThan(0)
  	const stored = JSON.parse(calls[calls.length - 1][1])
  	__testAugmentVitest_5c718f26a041.expect(stored.apiConfigs.default.rateLimitSeconds).toEqual(0)
  	__testAugmentVitest_5c718f26a041.expect(stored.apiConfigs.test.rateLimitSeconds).toEqual(0)
  })
})

import * as __testAugmentVitest_5c718f26a041 from "vitest";

const __testAugmentLoadTarget_ab5aab55dd39 = async () => {
  __testAugmentVitest_5c718f26a041.vi.doUnmock("../ProviderSettingsManager.js");
  __testAugmentVitest_5c718f26a041.vi.resetModules();
  return import("../ProviderSettingsManager.js");
};
