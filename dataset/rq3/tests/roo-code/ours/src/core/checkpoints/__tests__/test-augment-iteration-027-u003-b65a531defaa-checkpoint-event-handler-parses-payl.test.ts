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





  __testAugmentVitest_5e41d6aa950a.it("checkpoint-event-handler_parses_payload_round_027", async () => {
  	// Create a mock service that records event handlers so we can invoke them.
  	const handlers: Record<string, Function> = {}
  	const mockService = {
  		on: (event: string, cb: Function) => { handlers[event] = cb },
  		initShadowGit: __testAugmentVitest_5e41d6aa950a.vi.fn().mockResolvedValue(undefined),
  		getDiff: __testAugmentVitest_5e41d6aa950a.vi.fn().mockResolvedValue([]),
  		isInitialized: true,
  	}

  	// Mock the checkpoints factory to return the above service
  	__testAugmentVitest_5e41d6aa950a.vi.doMock("../../../services/checkpoints", () => ({
  		RepoPerTaskCheckpointService: { create: __testAugmentVitest_5e41d6aa950a.vi.fn().mockReturnValue(mockService) },
  	}))

  	// Ensure provider has storage and is available
  	mockTask.providerRef = { deref: () => ({ ...mockProvider, context: { globalStorageUri: { fsPath: "/test/storage" } } }) }
  	mockTask.enableCheckpoints = true
  	mockTask.checkpointService = undefined
  	mockTask.checkpointServiceInitializing = false

  	const { getCheckpointService } = await __testAugmentLoadTarget_fb94aaf59838()
  	const service = await getCheckpointService(mockTask)

  	// The on('checkpoint', ...) handler should have been registered. Simulate a checkpoint event.
  	__testAugmentVitest_5e41d6aa950a.expect(typeof handlers["checkpoint"]).toBe("function")

  	const payload = { fromHash: "from-hash", toHash: "to-hash", suppressMessage: true }
  	await handlers["checkpoint"](payload)

  	// Provider should receive currentCheckpointUpdated including suppressMessage flag
  	__testAugmentVitest_5e41d6aa950a.expect(mockProvider.postMessageToWebview).toHaveBeenCalledWith({
  		type: "currentCheckpointUpdated",
  		text: "to-hash",
  		suppressMessage: true,
  	})

  	// Task.say should be invoked with the checkpoint_saved payload and include the from/to and suppress flag
  	__testAugmentVitest_5e41d6aa950a.expect(mockTask.say).toHaveBeenCalled()
  	const sayCall = (__testAugmentVitest_5e41d6aa950a.vi.mocked(mockTask.say) as any).mock.calls[0]
  	__testAugmentVitest_5e41d6aa950a.expect(sayCall[0]).toBe("checkpoint_saved")
  	__testAugmentVitest_5e41d6aa950a.expect(sayCall[1]).toBe("to-hash")
  	__testAugmentVitest_5e41d6aa950a.expect(sayCall[4]).toEqual({ from: "from-hash", to: "to-hash", suppressMessage: true })
  })
})

import * as __testAugmentVitest_5e41d6aa950a from "vitest";

const __testAugmentLoadTarget_fb94aaf59838 = async () => {
  __testAugmentVitest_5e41d6aa950a.vi.doUnmock("../index.js");
  __testAugmentVitest_5e41d6aa950a.vi.resetModules();
  return import("../index.js");
};
