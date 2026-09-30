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




  __testAugmentVitest_6005b8b76347.it("input_image_rooignore_denied_round_028_pass_02", async () => {
  	// Arrange: provider state valid, experiments enabled
  	mockCline.providerRef.deref().getState.mockResolvedValue({
  		experiments: { [EXPERIMENT_IDS.IMAGE_GENERATION]: true },
  		openRouterImageApiKey: "ok-key",
  		openRouterImageGenerationSelectedModel: "google/gemini-2.5-flash-image",
  	})

  	const inputImagePath = "secrets/source.png"
  	// Make rooIgnoreController deny access to the input image specifically
  	mockCline.rooIgnoreController.validateAccess = __testAugmentVitest_6005b8b76347.vi.fn().mockImplementation((p: string) => p !== inputImagePath)

  	const block = {
  		type: "tool_use",
  		name: "generate_image",
  		params: { prompt: "edit this", path: "dest.png", image: inputImagePath },
  		nativeArgs: { prompt: "edit this", path: "dest.png", image: inputImagePath },
  		partial: false,
  	}

  	// Ensure file exists so that flow reaches the validateAccess(inputImagePath) check
  	__testAugmentVitest_6005b8b76347.vi.mocked(fileUtils.fileExistsAtPath).mockResolvedValue(true)

  	// Act
  	await generateImageTool.handle(mockCline as Task, block as any, {
  		askApproval: mockAskApproval,
  		handleError: mockHandleError,
  		pushToolResult: mockPushToolResult,
  	})

  	// Assert: rooignore error for input image should be signaled and pushed
  	__testAugmentVitest_6005b8b76347.expect(mockCline.say).toHaveBeenCalledWith("rooignore_error", inputImagePath)
  	__testAugmentVitest_6005b8b76347.expect(mockPushToolResult).toHaveBeenCalledWith(formatResponse.rooIgnoreError(inputImagePath))
  })
})

import * as __testAugmentVitest_6005b8b76347 from "vitest";

const __testAugmentLoadTarget_cbe7001624fa = async () => {
  __testAugmentVitest_6005b8b76347.vi.doUnmock("../GenerateImageTool.js");
  __testAugmentVitest_6005b8b76347.vi.resetModules();
  return import("../GenerateImageTool.js");
};
