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








  __testAugmentVitest_5c718f26a041.it("sanitize_non_string-apiProvider_resets_round_029_pass_03", async () => {
  	// Arrange: config where apiProvider is present but not a string (e.g., number)
  	mockSecrets.get.mockResolvedValueOnce(
  		JSON.stringify({
  			currentApiConfigName: "some",
  			apiConfigs: {
  				bad: {
  					id: "bad-id",
  					apiProvider: 42,
  					apiKey: "whatever",
  				},
  			},
  			migrations: {},
  		}),
  	)

  	const local = new ProviderSettingsManager(mockContext)
  	await local.initialize()

  	const calls = mockSecrets.store.mock.calls
  	__testAugmentVitest_5c718f26a041.expect(calls.length).toBeGreaterThan(0)
  	const stored = JSON.parse(calls[calls.length - 1][1])
  	// apiProvider should have been removed (reset to undefined) while id remains
  	__testAugmentVitest_5c718f26a041.expect(stored.apiConfigs.bad).toBeDefined()
  	__testAugmentVitest_5c718f26a041.expect(stored.apiConfigs.bad.apiProvider).toBeUndefined()
  	__testAugmentVitest_5c718f26a041.expect(stored.apiConfigs.bad.id).toBe("bad-id")
  })
})

import * as __testAugmentVitest_5c718f26a041 from "vitest";

const __testAugmentLoadTarget_ab5aab55dd39 = async () => {
  __testAugmentVitest_5c718f26a041.vi.doUnmock("../ProviderSettingsManager.js");
  __testAugmentVitest_5c718f26a041.vi.resetModules();
  return import("../ProviderSettingsManager.js");
};
