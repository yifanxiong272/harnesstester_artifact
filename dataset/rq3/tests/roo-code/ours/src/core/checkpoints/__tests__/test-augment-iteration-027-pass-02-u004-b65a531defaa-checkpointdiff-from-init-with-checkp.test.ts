import { describe, it, expect, vi, beforeEach, afterEach, Mock } from "vitest"
import { Task } from "../../task/Task"
import { ClineProvider } from "../../webview/ClineProvider"
import { checkpointSave, checkpointRestore, checkpointDiff, getCheckpointService } from "../index"
import { MessageManager } from "../../message-manager"
import * as vscode from "vscode"

// Mock vscode
vi.mock("vscode", () => ({
	window: {
		showErrorMessage: vi.fn(),
		createTextEditorDecorationType: vi.fn(() => ({})),
		showInformationMessage: vi.fn(),
	},
	Uri: {
		file: vi.fn((path: string) => ({ fsPath: path })),
		parse: vi.fn((uri: string) => ({ with: vi.fn(() => ({})) })),
	},
	commands: {
		executeCommand: vi.fn(),
	},
}))

// Mock other dependencies

vi.mock("../../../utils/path", () => ({
	getWorkspacePath: vi.fn(() => "/test/workspace"),
}))

vi.mock("../../../utils/git", () => ({
	checkGitInstalled: vi.fn().mockResolvedValue(true),
}))

vi.mock("../../../i18n", () => ({
	t: vi.fn((key: string, options?: Record<string, any>) => {
		if (key === "common:errors.wait_checkpoint_long_time") {
			return `Checkpoint initialization is taking longer than ${options?.timeout} seconds...`
		}
		if (key === "common:errors.init_checkpoint_fail_long_time") {
			return `Checkpoint initialization failed after ${options?.timeout} seconds`
		}
		return key
	}),
}))

// Mock p-wait-for to control timeout behavior
vi.mock("p-wait-for", () => ({
	default: vi.fn(),
}))

vi.mock("../../../services/checkpoints")

describe("Checkpoint functionality", () => {
	let mockProvider: any
	let mockTask: any
	let mockCheckpointService: any

	beforeEach(async () => {
		// Create mock checkpoint service
		mockCheckpointService = {
			isInitialized: true,
			saveCheckpoint: vi.fn().mockResolvedValue({ commit: "test-commit-hash" }),
			restoreCheckpoint: vi.fn().mockResolvedValue(undefined),
			getDiff: vi.fn().mockResolvedValue([]),
			on: vi.fn(),
			initShadowGit: vi.fn().mockResolvedValue(undefined),
		}

		// Create mock provider
		mockProvider = {
			context: {
				globalStorageUri: { fsPath: "/test/storage" },
			},
			log: vi.fn(),
			postMessageToWebview: vi.fn(),
			postStateToWebview: vi.fn(),
			cancelTask: vi.fn(),
		}

		// Create mock task
		mockTask = {
			taskId: "test-task-id",
			enableCheckpoints: true,
			checkpointService: mockCheckpointService,
			checkpointServiceInitializing: false,
			providerRef: {
				deref: () => mockProvider,
			},
			clineMessages: [],
			apiConversationHistory: [],
			pendingUserMessageCheckpoint: undefined,
			say: vi.fn().mockResolvedValue(undefined),
			overwriteClineMessages: vi.fn(),
			overwriteApiConversationHistory: vi.fn(),
			combineMessages: vi.fn().mockReturnValue([]),
		}
		mockTask.messageManager = new MessageManager(mockTask)

		// Update the mock to return our mockCheckpointService
		const checkpointsModule = await import("../../../services/checkpoints")
		vi.mocked(checkpointsModule.RepoPerTaskCheckpointService.create).mockReturnValue(mockCheckpointService)
	})

	afterEach(() => {
		vi.clearAllMocks()
	})





  __testAugmentVitest_5e41d6aa950a.it("checkpointDiff_from_init_with_checkpoints_round_027_pass_02", async () => {
  	// Use the suite-level mocks (mockCheckpointService, mockTask, mockProvider)
  	// Prepare two checkpoints so 'from-init' chooses the first as fromHash
  	mockTask.clineMessages = [
  		{ ts: 1, say: "checkpoint_saved", text: "commit1" },
  		{ ts: 2, say: "checkpoint_saved", text: "commit2" },
  	]

  	const mockChanges = [
  		{
  			paths: { absolute: "/test/file.ts", relative: "file.ts" },
  			content: { before: "old", after: "new" },
  		},
  	]
  	mockCheckpointService.getDiff.mockResolvedValue(mockChanges)

  	// Access target via the static namespace injected by the harness
  	const { checkpointDiff } = __testAugmentTarget_fb94aaf59838
  	await checkpointDiff(mockTask, { ts: 2, previousCommitHash: undefined, commitHash: "commit2", mode: "from-init" })

  	// Expect the diff was requested from the first checkpoint to the selected one
  	__testAugmentVitest_5e41d6aa950a.expect(mockCheckpointService.getDiff).toHaveBeenCalledWith({ from: "commit1", to: "commit2" })
  	__testAugmentVitest_5e41d6aa950a.expect(__testAugmentVitest_5e41d6aa950a.vi.mocked((await import("vscode")).commands.executeCommand)).toHaveBeenCalledWith(
  		"vscode.changes",
  		"common:errors.checkpoint_diff_since_first",
  		expect.any(Array),
  	)
  })
})

import * as __testAugmentVitest_5e41d6aa950a from "vitest";

import * as __testAugmentTarget_fb94aaf59838 from "../index.js";

const __testAugmentLoadTarget_fb94aaf59838 = async () => {
  __testAugmentVitest_5e41d6aa950a.vi.doUnmock("../index.js");
  __testAugmentVitest_5e41d6aa950a.vi.resetModules();
  return import("../index.js");
};
