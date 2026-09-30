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








  __testAugmentVitest_5c718f26a041.it("migrate_openai_does_not_overwrite_when_openaiheaders_present_round_029_pass_03", async () => {
  	// Arrange: a config that has both openAiHostHeader (deprecated) and a non-empty openAiHeaders
  	mockSecrets.get.mockResolvedValueOnce(
  		JSON.stringify({
  			currentApiConfigName: "default",
  			apiConfigs: {
  				default: {
  					id: "d1",
  					openAiHostHeader: "legacy.host.example",
  					openAiHeaders: { Existing: "keep-me" },
  				},
  			},
  			migrations: { openAiHeadersMigrated: false },
  		}),
  	)

  	// Create a fresh manager so its initialize reads the mocked secrets.get
  	const local = new ProviderSettingsManager(mockContext)
  	// Ensure migrations complete
  	await local.initialize()

  	// Assert: openAiHeaders should remain untouched and openAiHostHeader should still exist
  	const calls = mockSecrets.store.mock.calls
  	__testAugmentVitest_5c718f26a041.expect(calls.length).toBeGreaterThan(0)
  	const stored = JSON.parse(calls[calls.length - 1][1])
  	__testAugmentVitest_5c718f26a041.expect(stored.apiConfigs.default.openAiHeaders).toEqual({ Existing: "keep-me" })
  	__testAugmentVitest_5c718f26a041.expect(stored.apiConfigs.default.openAiHostHeader).toBe("legacy.host.example")
  	__testAugmentVitest_5c718f26a041.expect(stored.migrations.openAiHeadersMigrated).toBe(true)
  })
})

import * as __testAugmentVitest_5c718f26a041 from "vitest";

const __testAugmentLoadTarget_ab5aab55dd39 = async () => {
  __testAugmentVitest_5c718f26a041.vi.doUnmock("../ProviderSettingsManager.js");
  __testAugmentVitest_5c718f26a041.vi.resetModules();
  return import("../ProviderSettingsManager.js");
};
