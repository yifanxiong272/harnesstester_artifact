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




  __testAugmentVitest_6005b8b76347.it("input_image_jpg_mime_mapping_round_028_pass_03", async () => {
  	// Arrange: ensure experiments enabled and API key present
  	mockCline.providerRef.deref().getState.mockResolvedValue({
  		experiments: { [EXPERIMENT_IDS.IMAGE_GENERATION]: true },
  		openRouterImageApiKey: "ok-key",
  		openRouterImageGenerationSelectedModel: "google/gemini-2.5-flash-image",
  	})

  	const inputImagePath = "assets/pic.jpg"
  	const block = {
  		type: "tool_use",
  		name: "generate_image",
  		params: { prompt: "edit it", path: "out.png", image: inputImagePath },
  		nativeArgs: { prompt: "edit it", path: "out.png", image: inputImagePath },
  		partial: false,
  	}

  	// file exists and access allowed
  	__testAugmentVitest_6005b8b76347.vi.mocked(fileUtils.fileExistsAtPath).mockResolvedValue(true)
  	mockCline.rooIgnoreController.validateAccess = __testAugmentVitest_6005b8b76347.vi.fn().mockReturnValue(true)

  	// readFile returns a small buffer; .jpg extension should map to mimeType 'jpeg'
  	__testAugmentVitest_6005b8b76347.vi.mocked(fs.readFile).mockResolvedValue(Buffer.from("abc"))

  	// Mock OpenRouterHandler.generateImage and capture the passed inputImageData arg
  	const mockGenerateImage = __testAugmentVitest_6005b8b76347.vi.fn().mockResolvedValue({ success: true, imageData: "data:image/png;base64,ZmFrZQ==" })
  	__testAugmentVitest_6005b8b76347.vi.mocked(OpenRouterHandler).mockImplementation(() => ({ generateImage: mockGenerateImage }) as any)

  	// Act
  	await generateImageTool.handle(mockCline as Task, block as any, {
  		askApproval: mockAskApproval,
  		handleError: mockHandleError,
  		pushToolResult: mockPushToolResult,
  	})

  	// Assert: generateImage called and the inputImageData passed uses jpeg mime for .jpg
  	__testAugmentVitest_6005b8b76347.expect(mockGenerateImage).toHaveBeenCalled()
  	const callArgs = mockGenerateImage.mock.calls[0]
  	// arg index 3 is inputImageData
  	__testAugmentVitest_6005b8b76347.expect(callArgs[3]).toEqual(__testAugmentVitest_6005b8b76347.expect.stringMatching(/^data:image\/jpeg;base64,[A-Za-z0-9+/=]+$/))
  })
})

import * as __testAugmentVitest_6005b8b76347 from "vitest";

const __testAugmentLoadTarget_cbe7001624fa = async () => {
  __testAugmentVitest_6005b8b76347.vi.doUnmock("../GenerateImageTool.js");
  __testAugmentVitest_6005b8b76347.vi.resetModules();
  return import("../GenerateImageTool.js");
};
