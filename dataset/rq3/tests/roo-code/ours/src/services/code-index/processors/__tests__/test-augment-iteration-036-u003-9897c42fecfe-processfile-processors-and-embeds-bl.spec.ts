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



	  __testAugmentVitest_26ac3d5d031a.it("processFile processors and embeds blocks into points_round_036", async () => {
	  	// Arrange: ensure parser returns a single code block and cache says file changed
	  	const parserModule = await import("../parser")
	  	// Provide a single block with expected shape
	  	parserModule.codeParser.parseFile.mockResolvedValue([
	  		{
	  			file_path: "/mock/workspace/src/file.ts",
	  			content: "const a = 1;",
	  			start_line: 1,
	  			end_line: 1,
	  		},
	  	])

	  	// Make cacheManager indicate there is no previous hash (so processing proceeds)
	  	mockCacheManager.getHash.mockReturnValue(undefined)

	  	// Ensure fs.readFile returns the same content buffer used above
	  	const contentBuffer = Buffer.from("const a = 1;")
	  	__testAugmentVitest_26ac3d5d031a.vi.mocked(vscode.workspace.fs.readFile).mockResolvedValue(contentBuffer)
	  	__testAugmentVitest_26ac3d5d031a.vi.mocked(vscode.workspace.fs.stat).mockResolvedValue({ size: 100 })

	  	// Act
	  	const result = await fileWatcher.processFile("/mock/workspace/src/file.ts")

	  	// Assert: processed_for_batching with points created
	  	__testAugmentVitest_26ac3d5d031a.expect(result.status).toBe("processed_for_batching")
	  	__testAugmentVitest_26ac3d5d031a.expect(result.pointsToUpsert).toBeDefined()
	  	__testAugmentVitest_26ac3d5d031a.expect(Array.isArray(result.pointsToUpsert)).toBe(true)
	  	__testAugmentVitest_26ac3d5d031a.expect((result.pointsToUpsert || []).length).toBe(1)
	  	const point = (result.pointsToUpsert || [])[0]
	  	__testAugmentVitest_26ac3d5d031a.expect(point.payload).toBeDefined()
	  	__testAugmentVitest_26ac3d5d031a.expect(point.payload.codeChunk).toBe("const a = 1;")
	  	// newHash should be present
	  	__testAugmentVitest_26ac3d5d031a.expect(typeof (result as any).newHash).toBe("string")
	  })
	})

})

import * as __testAugmentVitest_26ac3d5d031a from "vitest";

const __testAugmentLoadTarget_db507061bb58 = async () => {
  __testAugmentVitest_26ac3d5d031a.vi.doUnmock("../file-watcher.js");
  __testAugmentVitest_26ac3d5d031a.vi.resetModules();
  return import("../file-watcher.js");
};
