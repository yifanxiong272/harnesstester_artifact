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








  __testAugmentVitest_5c718f26a041.it("set_mode_config_creates_map_and_gets_it_round_029_pass_02", async () => {
  	// Arrange: ensure the next load() will return a profile without modeApiConfigs
  	mockSecrets.get.mockResolvedValueOnce(
  		JSON.stringify({
  			currentApiConfigName: "default",
  			apiConfigs: { default: { id: "d1" } },
  			migrations: {},
  		}),
  	)

  	// Create a fresh instance so its constructor.initialize uses the mocked secrets.get
  	const localMgr = new ProviderSettingsManager(mockContext)

  	// Act: set the mode config for 'code' to a deterministic id
  	await localMgr.setModeConfig("code" as any, "cfg-123")

  	// Assert: the persisted profile contains the created modeApiConfigs map with our entry
  	const calls = mockSecrets.store.mock.calls
  	__testAugmentVitest_5c718f26a041.expect(calls.length).toBeGreaterThan(0)
  	const stored = JSON.parse(calls[calls.length - 1][1])
  	__testAugmentVitest_5c718f26a041.expect(stored.modeApiConfigs).toBeDefined()
  	__testAugmentVitest_5c718f26a041.expect(stored.modeApiConfigs.code).toBe("cfg-123")

  	// And verifying the getter returns the assigned value
  	const modeId = await localMgr.getModeConfigId("code" as any)
  	__testAugmentVitest_5c718f26a041.expect(modeId).toBe("cfg-123")
  })
})

import * as __testAugmentVitest_5c718f26a041 from "vitest";

const __testAugmentLoadTarget_ab5aab55dd39 = async () => {
  __testAugmentVitest_5c718f26a041.vi.doUnmock("../ProviderSettingsManager.js");
  __testAugmentVitest_5c718f26a041.vi.resetModules();
  return import("../ProviderSettingsManager.js");
};
