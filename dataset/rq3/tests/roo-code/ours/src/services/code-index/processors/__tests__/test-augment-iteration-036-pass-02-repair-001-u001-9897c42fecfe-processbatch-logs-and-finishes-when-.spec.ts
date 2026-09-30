// npx vitest services/code-index/processors/__tests__/file-watcher.spec.ts

import * as vscode from "vscode"

import { FileWatcher } from "../file-watcher"

// Mock dependencies
vi.mock("../../cache-manager")
vi.mock("../../../core/ignore/RooIgnoreController", () => ({
	RooIgnoreController: vi.fn().mockImplementation(() => ({
		validateAccess: vi.fn().mockReturnValue(true),
	})),
}))
vi.mock("ignore")
vi.mock("../parser", () => ({
	codeParser: {
		parseFile: vi.fn().mockResolvedValue([]),
	},
}))
vi.mock("../../../glob/ignore-utils", () => ({
	isPathInIgnoredDirectory: vi.fn().mockReturnValue(false),
}))

// Mock vscode module
vi.mock("vscode", () => ({
	workspace: {
		createFileSystemWatcher: vi.fn(),
		workspaceFolders: [
			{
				uri: {
					fsPath: "/mock/workspace",
				},
			},
		],
		fs: {
			stat: vi.fn().mockResolvedValue({ size: 1000 }),
			readFile: vi.fn().mockResolvedValue(Buffer.from("test content")),
		},
	},
	RelativePattern: vi.fn().mockImplementation((base, pattern) => ({ base, pattern })),
	Uri: {
		file: vi.fn().mockImplementation((path) => ({ fsPath: path })),
	},
	EventEmitter: vi.fn().mockImplementation(() => ({
		event: vi.fn(),
		fire: vi.fn(),
		dispose: vi.fn(),
	})),
	ExtensionContext: vi.fn(),
}))

describe("FileWatcher", () => {
	let fileWatcher: FileWatcher
	let mockWatcher: any
	let mockOnDidCreate: any
	let mockOnDidChange: any
	let mockOnDidDelete: any
	let mockContext: any
	let mockCacheManager: any
	let mockEmbedder: any
	let mockVectorStore: any
	let mockIgnoreInstance: any

	beforeEach(() => {
		// Reset all mocks
		vi.clearAllMocks()

		// Create mock event handlers
		mockOnDidCreate = vi.fn()
		mockOnDidChange = vi.fn()
		mockOnDidDelete = vi.fn()

		// Create mock watcher
		mockWatcher = {
			onDidCreate: vi.fn().mockImplementation((handler) => {
				mockOnDidCreate = handler
				return { dispose: vi.fn() }
			}),
			onDidChange: vi.fn().mockImplementation((handler) => {
				mockOnDidChange = handler
				return { dispose: vi.fn() }
			}),
			onDidDelete: vi.fn().mockImplementation((handler) => {
				mockOnDidDelete = handler
				return { dispose: vi.fn() }
			}),
			dispose: vi.fn(),
		}

		// Mock createFileSystemWatcher to return our mock watcher
		vi.mocked(vscode.workspace.createFileSystemWatcher).mockReturnValue(mockWatcher)

		// Create mock dependencies
		mockContext = {
			subscriptions: [],
		}

		mockCacheManager = {
			getHash: vi.fn(),
			updateHash: vi.fn(),
			deleteHash: vi.fn(),
		}

		mockEmbedder = {
			createEmbeddings: vi.fn().mockResolvedValue({ embeddings: [[0.1, 0.2, 0.3]] }),
		}

		mockVectorStore = {
			upsertPoints: vi.fn().mockResolvedValue(undefined),
			deletePointsByFilePath: vi.fn().mockResolvedValue(undefined),
			deletePointsByMultipleFilePaths: vi.fn().mockResolvedValue(undefined),
		}

		mockIgnoreInstance = {
			ignores: vi.fn().mockReturnValue(false),
		}

		fileWatcher = new FileWatcher(
			"/mock/workspace",
			mockContext,
			mockCacheManager,
			mockEmbedder,
			mockVectorStore,
			mockIgnoreInstance,
		)
	})

	describe("file filtering", () => {



	  __testAugmentVitest_26ac3d5d031a.it("processBatch logs and finishes when processFile throws_round_036_pass_02", async () => {
	  	// Arrange: single file whose processFile will throw to exercise the directError branch
	  	const badPath = "/mock/workspace/src/direct_throw.ts"
	  	const eventsToProcess = new Map<string, any>()
	  	eventsToProcess.set(badPath, { uri: vscode.Uri.file(badPath), type: "change" })

	  	// Replace instance processFile: throw for this test
	  	;(fileWatcher as any).processFile = __testAugmentVitest_26ac3d5d031a.vi.fn()
	  	__testAugmentVitest_26ac3d5d031a.vi.mocked((fileWatcher as any).processFile).mockImplementationOnce(async () => {
	  		throw new Error("simulated failure")
	  	})

	  	// Spy on console.error to assert the catch branch logged the exception
	  	const consoleErrorMock = __testAugmentVitest_26ac3d5d031a.vi.spyOn(console, "error").mockImplementation(() => {})

	  	// Act
	  	await (fileWatcher as any).processBatch(eventsToProcess)

	  	// Assert: console.error was called for the thrown file and the finish event was fired with at least one processedFiles entry
	  	__testAugmentVitest_26ac3d5d031a.expect(consoleErrorMock).toHaveBeenCalled()

	  	const finishCalls = __testAugmentVitest_26ac3d5d031a.vi.mocked((fileWatcher as any)._onDidFinishBatchProcessing.fire).mock.calls
	  	__testAugmentVitest_26ac3d5d031a.expect(finishCalls.length).toBeGreaterThanOrEqual(1)
	  	const summary = finishCalls[finishCalls.length - 1][0]
	  	__testAugmentVitest_26ac3d5d031a.expect(Array.isArray(summary.processedFiles)).toBe(true)
	  	__testAugmentVitest_26ac3d5d031a.expect((summary.processedFiles as any[]).length).toBeGreaterThanOrEqual(1)

	  	// Cleanup spy
	  	consoleErrorMock.mockRestore()
	  })
	})

})

import * as __testAugmentVitest_26ac3d5d031a from "vitest";

const __testAugmentLoadTarget_db507061bb58 = async () => {
  __testAugmentVitest_26ac3d5d031a.vi.doUnmock("../file-watcher.js");
  __testAugmentVitest_26ac3d5d031a.vi.resetModules();
  return import("../file-watcher.js");
};
