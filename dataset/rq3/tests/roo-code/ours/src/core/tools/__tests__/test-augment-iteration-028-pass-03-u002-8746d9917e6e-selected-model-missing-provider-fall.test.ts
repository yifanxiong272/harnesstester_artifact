import { describe, it, expect, vi, beforeEach } from "vitest"
import { generateImageTool } from "../GenerateImageTool"
import { ToolUse } from "../../../shared/tools"
import { Task } from "../../task/Task"
import * as fs from "fs/promises"
import * as pathUtils from "../../../utils/pathUtils"
import * as fileUtils from "../../../utils/fs"
import { formatResponse } from "../../prompts/responses"
import { EXPERIMENT_IDS } from "../../../shared/experiments"
import { OpenRouterHandler } from "../../../api/providers/openrouter"

// Mock dependencies
vi.mock("fs/promises")
vi.mock("../../../utils/pathUtils")
vi.mock("../../../utils/fs")
vi.mock("../../../utils/safeWriteJson")
vi.mock("../../../api/providers/openrouter")

describe("generateImageTool", () => {
	let mockCline: any
	let mockAskApproval: any
	let mockHandleError: any
	let mockPushToolResult: any

	beforeEach(() => {
		vi.clearAllMocks()

		// Setup mock Cline instance
		mockCline = {
			cwd: "/test/workspace",
			consecutiveMistakeCount: 0,
			recordToolError: vi.fn(),
			recordToolUsage: vi.fn(),
			sayAndCreateMissingParamError: vi.fn().mockResolvedValue("Missing parameter error"),
			say: vi.fn(),
			rooIgnoreController: {
				validateAccess: vi.fn().mockReturnValue(true),
			},
			rooProtectedController: {
				isWriteProtected: vi.fn().mockReturnValue(false),
			},
			providerRef: {
				deref: vi.fn().mockReturnValue({
					getState: vi.fn().mockResolvedValue({
						experiments: {
							[EXPERIMENT_IDS.IMAGE_GENERATION]: true,
						},
						openRouterImageApiKey: "test-api-key",
						openRouterImageGenerationSelectedModel: "google/gemini-2.5-flash-image",
					}),
				}),
			},
			fileContextTracker: {
				trackFileContext: vi.fn(),
			},
			didEditFile: false,
		}

		mockAskApproval = vi.fn().mockResolvedValue(true)
		mockHandleError = vi.fn()
		mockPushToolResult = vi.fn()

		// Mock file system operations
		vi.mocked(fileUtils.fileExistsAtPath).mockResolvedValue(true)
		vi.mocked(fs.readFile).mockResolvedValue(Buffer.from("fake-image-data"))
		vi.mocked(fs.mkdir).mockResolvedValue(undefined)
		vi.mocked(fs.writeFile).mockResolvedValue(undefined)
		vi.mocked(pathUtils.isPathOutsideWorkspace).mockReturnValue(false)
	})




  __testAugmentVitest_6005b8b76347.it("selected_model_missing_provider_fallback_round_028_pass_03", async () => {
  	// We must mock the '@roo-code/types' imports before loading the target so provider models are deterministic
  	__testAugmentVitest_6005b8b76347.vi.doMock("@roo-code/types", () => ({
  		// Minimal shapes required by GenerateImageTool
  		IMAGE_GENERATION_MODEL_IDS: ["fallback-id"],
  		IMAGE_GENERATION_MODELS: [
  			{ provider: "myprov", value: "fallback-model", apiMethod: "generate" },
  		],
  		getImageGenerationProvider: (stateProvider: any, openrouterFlag: boolean) => "myprov",
  		// Expose constants/types that other code may reference (no-op placeholders)
  		GenerateImageParams: {},
  		export: {},
  	}))

  	// Load the target after mocking the types module
  	const target = await __testAugmentLoadTarget_cbe7001624fa()
  	const { generateImageTool } = target as any

  	// Arrange: selected model is set to something that won't be found for provider "myprov"
  	mockCline.providerRef.deref().getState.mockResolvedValue({
  		experiments: { [EXPERIMENT_IDS.IMAGE_GENERATION]: true },
  		openRouterImageApiKey: "ok-key",
  		openRouterImageGenerationSelectedModel: "nonexistent-model",
  		imageGenerationProvider: undefined,
  	})

  	// Provide minimal success response so flow continues to provider call
  	const mockGenerateImage = __testAugmentVitest_6005b8b76347.vi.fn().mockResolvedValue({ success: true, imageData: "data:image/png;base64,ZmFrZQ==" })
  	__testAugmentVitest_6005b8b76347.vi.mocked(OpenRouterHandler).mockImplementation(() => ({ generateImage: mockGenerateImage }) as any)

  	const block = {
  		type: "tool_use",
  		name: "generate_image",
  		params: { prompt: "prompt", path: "out.png" },
  		nativeArgs: { prompt: "prompt", path: "out.png" },
  		partial: false,
  	}

  	// Ensure filesystem writes succeed
  	__testAugmentVitest_6005b8b76347.vi.mocked(fs.mkdir).mockResolvedValue(undefined)
  	__testAugmentVitest_6005b8b76347.vi.mocked(fs.writeFile).mockResolvedValue(undefined)

  	// Act
  	await generateImageTool.handle(mockCline as Task, block as any, {
  		askApproval: mockAskApproval,
  		handleError: mockHandleError,
  		pushToolResult: mockPushToolResult,
  	})

  	// Assert: generateImage called and selectedModel fallback ('fallback-model') used as second arg
  	__testAugmentVitest_6005b8b76347.expect(mockGenerateImage).toHaveBeenCalled()
  	const selectedModelArg = mockGenerateImage.mock.calls[0][1]
  	__testAugmentVitest_6005b8b76347.expect(selectedModelArg).toBe("fallback-model")
  })
})

import * as __testAugmentVitest_6005b8b76347 from "vitest";

const __testAugmentLoadTarget_cbe7001624fa = async () => {
  __testAugmentVitest_6005b8b76347.vi.doUnmock("../GenerateImageTool.js");
  __testAugmentVitest_6005b8b76347.vi.resetModules();
  return import("../GenerateImageTool.js");
};
