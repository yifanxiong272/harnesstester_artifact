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





  __testAugmentVitest_5e41d6aa950a.it("initShadowGit_failure_disables_round_027_pass_02", async () => {
  	// Service where initShadowGit fails
  	const mockService = {
  		on: __testAugmentVitest_5e41d6aa950a.vi.fn(),
  		initShadowGit: __testAugmentVitest_5e41d6aa950a.vi.fn().mockRejectedValue(new Error("boom")),
  		isInitialized: true,
  	}

  	__testAugmentVitest_5e41d6aa950a.vi.doMock("../../../services/checkpoints", () => ({
  		RepoPerTaskCheckpointService: { create: __testAugmentVitest_5e41d6aa950a.vi.fn().mockReturnValue(mockService) },
  	}))

  	// Ensure we get to the Git-check and initShadowGit call
  	mockTask.checkpointService = undefined
  	mockTask.checkpointServiceInitializing = false
  	mockTask.enableCheckpoints = true
  	mockTask.providerRef = { deref: () => ({ ...mockProvider, context: { globalStorageUri: { fsPath: "/test/storage" } } }) }

  	const { getCheckpointService } = await __testAugmentLoadTarget_fb94aaf59838()
  	const svc = await getCheckpointService(mockTask)

  	// initShadowGit rejected, so the code should have logged the initShadowGit error and disabled checkpoints
  	__testAugmentVitest_5e41d6aa950a.expect(mockProvider.log).toHaveBeenCalled()
  	const logged = (__testAugmentVitest_5e41d6aa950a.vi.mocked(mockProvider.log) as any).mock.calls.flat().join(' ')
  	__testAugmentVitest_5e41d6aa950a.expect(logged).toContain("initShadowGit -> boom")
  	__testAugmentVitest_5e41d6aa950a.expect(mockTask.enableCheckpoints).toBe(false)
  	// Service instance should still be returned (no throw), but checkpoints disabled
  	__testAugmentVitest_5e41d6aa950a.expect(svc).toBe(mockService)
  })
})

import * as __testAugmentVitest_5e41d6aa950a from "vitest";

const __testAugmentLoadTarget_fb94aaf59838 = async () => {
  __testAugmentVitest_5e41d6aa950a.vi.doUnmock("../index.js");
  __testAugmentVitest_5e41d6aa950a.vi.resetModules();
  return import("../index.js");
};
