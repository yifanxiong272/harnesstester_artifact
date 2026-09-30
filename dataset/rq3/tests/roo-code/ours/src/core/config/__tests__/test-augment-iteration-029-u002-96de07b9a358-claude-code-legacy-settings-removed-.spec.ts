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








  __testAugmentVitest_5c718f26a041.it("claude_code_legacy_settings_removed_round_029", async () => {
  	// Arrange: include a config that simulates the old claude-code provider with legacy keys
  	mockSecrets.get.mockResolvedValueOnce(
  		JSON.stringify({
  			currentApiConfigName: "default",
  			apiConfigs: {
  				oldClaude: {
  					id: "old-claude-id",
  					apiProvider: "claude-code",
  					claudeCodePath: "/usr/local/claude",
  					claudeCodeMaxOutputTokens: 9999,
  				},
  			},
  			migrations: { claudeCodeLegacySettingsMigrated: false },
  		}),
  	)

  	// Act
  	await providerSettingsManager.initialize()

  	// Assert: legacy claude-code keys should be removed and migration flag set
  	const calls = mockSecrets.store.mock.calls
  	__testAugmentVitest_5c718f26a041.expect(calls.length).toBeGreaterThan(0)
  	const stored = JSON.parse(calls[calls.length - 1][1])
  	__testAugmentVitest_5c718f26a041.expect(stored.apiConfigs.oldClaude.claudeCodePath).toBeUndefined()
  	__testAugmentVitest_5c718f26a041.expect(stored.apiConfigs.oldClaude.claudeCodeMaxOutputTokens).toBeUndefined()
  	__testAugmentVitest_5c718f26a041.expect(stored.migrations.claudeCodeLegacySettingsMigrated).toBe(true)
  })
})

import * as __testAugmentVitest_5c718f26a041 from "vitest";

const __testAugmentLoadTarget_ab5aab55dd39 = async () => {
  __testAugmentVitest_5c718f26a041.vi.doUnmock("../ProviderSettingsManager.js");
  __testAugmentVitest_5c718f26a041.vi.resetModules();
  return import("../ProviderSettingsManager.js");
};
