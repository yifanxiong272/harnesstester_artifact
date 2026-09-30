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








  __testAugmentVitest_5c718f26a041.it("clean_model_id_slash_stripping_round_029", async () => {
  	// Arrange: a config with a model id that contains a prefix and '/'
  	mockSecrets.get.mockResolvedValueOnce(
  		JSON.stringify({
  			currentApiConfigName: "default",
  			apiConfigs: {
  				default: {
  					id: "d1",
  					apiProvider: "openrouter",
  					apiModelId: "prefix/actual-model-name",
  				},
  			},
  			migrations: {},
  		}),
  	)

  	// Act
  	const list = await providerSettingsManager.listConfig()

  	// Assert: listConfig should return the modelId stripped to part after '/'
  	__testAugmentVitest_5c718f26a041.expect(list).toHaveLength(1)
  	__testAugmentVitest_5c718f26a041.expect(list[0].name).toBe("default")
  	__testAugmentVitest_5c718f26a041.expect(list[0].id).toBe("d1")
  	__testAugmentVitest_5c718f26a041.expect(list[0].modelId).toBe("actual-model-name")
  })
})

import * as __testAugmentVitest_5c718f26a041 from "vitest";

const __testAugmentLoadTarget_ab5aab55dd39 = async () => {
  __testAugmentVitest_5c718f26a041.vi.doUnmock("../ProviderSettingsManager.js");
  __testAugmentVitest_5c718f26a041.vi.resetModules();
  return import("../ProviderSettingsManager.js");
};
