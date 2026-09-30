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




  __testAugmentVitest_6005b8b76347.it("no_selected_model_fallback_and_extension_append_round_028_pass_02", async () => {
  	// Arrange: state with no selected model to hit the 'else' branch and fallback selection
  	mockCline.providerRef.deref().getState.mockResolvedValue({
  		experiments: { [EXPERIMENT_IDS.IMAGE_GENERATION]: true },
  		openRouterImageApiKey: "ok-key",
  		openRouterImageGenerationSelectedModel: undefined,
  		imageGenerationProvider: undefined,
  	})

  	// Prepare an OpenRouterHandler that returns a jpeg image so finalPath extension logic runs
  	const mockGenerateImage = __testAugmentVitest_6005b8b76347.vi.fn().mockResolvedValue({
  		success: true,
  		imageData: "data:image/jpeg;base64,ZmFrZQ==",
  	})
  	__testAugmentVitest_6005b8b76347.vi.mocked(OpenRouterHandler).mockImplementation(() => ({ generateImage: mockGenerateImage }) as any)

  	// Use a relPath without extension to force the extension-appending logic (line 228)
  	const block = {
  		type: "tool_use",
  		name: "generate_image",
  		params: { prompt: "render", path: "outputs/outfile" },
  		nativeArgs: { prompt: "render", path: "outputs/outfile" },
  		partial: false,
  	}

  	// Ensure file system ops succeed
  	__testAugmentVitest_6005b8b76347.vi.mocked(fs.mkdir).mockResolvedValue(undefined)
  	__testAugmentVitest_6005b8b76347.vi.mocked(fs.writeFile).mockResolvedValue(undefined)

  	// Act
  	await generateImageTool.handle(mockCline as Task, block as any, {
  		askApproval: mockAskApproval,
  		handleError: mockHandleError,
  		pushToolResult: mockPushToolResult,
  	})

  	// Assert: provider called and file written with .jpg appended; tracker called with appended filename
  	__testAugmentVitest_6005b8b76347.expect(mockGenerateImage).toHaveBeenCalled()
  	// trackFileContext should be called with out filename that now includes .jpg
  	__testAugmentVitest_6005b8b76347.expect(mockCline.fileContextTracker.trackFileContext).toHaveBeenCalledWith("outputs/outfile.jpg", "roo_edited")
  	// And a tool result should be pushed with readable path
  	__testAugmentVitest_6005b8b76347.expect(mockPushToolResult).toHaveBeenCalled()
  })
})

import * as __testAugmentVitest_6005b8b76347 from "vitest";

const __testAugmentLoadTarget_cbe7001624fa = async () => {
  __testAugmentVitest_6005b8b76347.vi.doUnmock("../GenerateImageTool.js");
  __testAugmentVitest_6005b8b76347.vi.resetModules();
  return import("../GenerateImageTool.js");
};
