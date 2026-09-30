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



	  __testAugmentVitest_26ac3d5d031a.it("processBatch handles settled rejection path_round_036_pass_02", async () => {
	  	// Arrange: two files; one will cause _onBatchProgressUpdate.fire to throw (so the chunk async function rejects), the other processes normally
	  	const badPath = "/mock/workspace/src/willReject.ts"
	  	const goodPath = "/mock/workspace/src/good.ts"
	  	const eventsToProcess = new Map<string, any>()
	  	eventsToProcess.set(badPath, { uri: vscode.Uri.file(badPath), type: "change" })
	  	eventsToProcess.set(goodPath, { uri: vscode.Uri.file(goodPath), type: "change" })

	  	// Make _onBatchProgressUpdate.fire throw only when currentFile === badPath
	  	const originalFire = (fileWatcher as any)._onBatchProgressUpdate.fire
	  	;(fileWatcher as any)._onBatchProgressUpdate.fire = (payload: any) => {
	  		if (payload?.currentFile === badPath) {
	  			throw { path: "rejected-custom", message: "forced rejection" }
	  		}
	  		return originalFire.call((fileWatcher as any)._onBatchProgressUpdate, payload)
	  	}

	  	// Ensure processFile for goodPath resolves to a processed_for_batching result
	  	;(fileWatcher as any).processFile = __testAugmentVitest_26ac3d5d031a.vi.fn()
	  	__testAugmentVitest_26ac3d5d031a.vi.mocked((fileWatcher as any).processFile).mockImplementation(async (p: string) => {
	  		if (p === goodPath) {
	  			return { path: goodPath, status: "processed_for_batching", pointsToUpsert: [] }
	  		}
	  		// For badPath, it won't reach processFile because the fire threw earlier
	  		return undefined
	  	})

	  	// Act
	  	await (fileWatcher as any).processBatch(eventsToProcess)

	  	// Assert: summary processedFiles should include an error with path 'rejected-custom' (from thrown object)
	  	const finishCalls = __testAugmentVitest_26ac3d5d031a.vi.mocked((fileWatcher as any)._onDidFinishBatchProcessing.fire).mock.calls
	  	__testAugmentVitest_26ac3d5d031a.expect(finishCalls.length).toBeGreaterThanOrEqual(1)
	  	const summary = finishCalls[finishCalls.length - 1][0]
	  	__testAugmentVitest_26ac3d5d031a.expect(summary.processedFiles.some((r: any) => r.path === "rejected-custom" && r.status === "error")).toBe(true)
	  })
	})

})

import * as __testAugmentVitest_26ac3d5d031a from "vitest";

const __testAugmentLoadTarget_db507061bb58 = async () => {
  __testAugmentVitest_26ac3d5d031a.vi.doUnmock("../file-watcher.js");
  __testAugmentVitest_26ac3d5d031a.vi.resetModules();
  return import("../file-watcher.js");
};
