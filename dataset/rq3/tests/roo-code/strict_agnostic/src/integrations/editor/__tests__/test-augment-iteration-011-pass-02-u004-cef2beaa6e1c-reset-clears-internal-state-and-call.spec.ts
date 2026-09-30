import { DiffViewProvider, DIFF_VIEW_URI_SCHEME, DIFF_VIEW_LABEL_CHANGES } from "../DiffViewProvider"
import * as vscode from "vscode"
import * as path from "path"
import delay from "delay"

// Mock delay
vi.mock("delay", () => ({
	default: vi.fn().mockResolvedValue(undefined),
}))

// Mock fs/promises
vi.mock("fs/promises", () => ({
	readFile: vi.fn().mockResolvedValue("file content"),
	writeFile: vi.fn().mockResolvedValue(undefined),
}))

// Mock utils
vi.mock("../../../utils/fs", () => ({
	createDirectoriesForFile: vi.fn().mockResolvedValue([]),
}))

// Mock path
vi.mock("path", () => ({
	resolve: vi.fn((cwd, relPath) => `${cwd}/${relPath}`),
	basename: vi.fn((path) => path.split("/").pop()),
}))

// Mock vscode
vi.mock("vscode", () => ({
	workspace: {
		applyEdit: vi.fn(),
		onDidOpenTextDocument: vi.fn(() => ({ dispose: vi.fn() })),
		openTextDocument: vi.fn().mockResolvedValue({
			isDirty: false,
			save: vi.fn().mockResolvedValue(undefined),
		}),
		textDocuments: [],
		fs: {
			stat: vi.fn(),
		},
	},
	window: {
		createTextEditorDecorationType: vi.fn(),
		showTextDocument: vi.fn(),
		onDidChangeVisibleTextEditors: vi.fn(() => ({ dispose: vi.fn() })),
		tabGroups: {
			all: [],
			close: vi.fn(),
		},
		visibleTextEditors: [],
	},
	commands: {
		executeCommand: vi.fn(),
	},
	languages: {
		getDiagnostics: vi.fn(() => []),
	},
	DiagnosticSeverity: {
		Error: 0,
		Warning: 1,
		Information: 2,
		Hint: 3,
	},
	WorkspaceEdit: vi.fn().mockImplementation(() => ({
		replace: vi.fn(),
		delete: vi.fn(),
	})),
	ViewColumn: {
		Active: 1,
		Beside: 2,
		One: 1,
		Two: 2,
		Three: 3,
		Four: 4,
		Five: 5,
		Six: 6,
		Seven: 7,
		Eight: 8,
		Nine: 9,
	},
	Range: vi.fn(),
	Position: vi.fn(),
	Selection: vi.fn(),
	TextEditorRevealType: {
		InCenter: 2,
	},
	TabInputTextDiff: class TabInputTextDiff {},
	Uri: {
		file: vi.fn((path) => ({ fsPath: path })),
		parse: vi.fn((uri) => ({ with: vi.fn(() => ({})) })),
	},
}))

// Mock DecorationController
vi.mock("../DecorationController", () => ({
	DecorationController: vi.fn().mockImplementation(() => ({
		setActiveLine: vi.fn(),
		updateOverlayAfterLine: vi.fn(),
		addLines: vi.fn(),
		clear: vi.fn(),
	})),
}))

describe("DiffViewProvider", () => {
	let diffViewProvider: DiffViewProvider
	const mockCwd = "/mock/cwd"
	let mockWorkspaceEdit: { replace: any; delete: any }
	let mockTask: any

	beforeEach(() => {
		vi.clearAllMocks()
		mockWorkspaceEdit = {
			replace: vi.fn(),
			delete: vi.fn(),
		}
		vi.mocked(vscode.WorkspaceEdit).mockImplementation(() => mockWorkspaceEdit as any)

		// Create a mock Task instance
		mockTask = {
			providerRef: {
				deref: vi.fn().mockReturnValue({
					getState: vi.fn().mockResolvedValue({
						includeDiagnosticMessages: true,
						maxDiagnosticMessages: 50,
					}),
				}),
			},
		}

		diffViewProvider = new DiffViewProvider(mockCwd, mockTask)
		// Mock the necessary properties and methods
		;(diffViewProvider as any).relPath = "test.txt"
		;(diffViewProvider as any).activeDiffEditor = {
			document: {
				uri: { fsPath: `${mockCwd}/test.txt` },
				getText: vi.fn(),
				lineCount: 10,
			},
			selection: {
				active: { line: 0, character: 0 },
				anchor: { line: 0, character: 0 },
			},
			edit: vi.fn().mockResolvedValue(true),
			revealRange: vi.fn(),
		}
		;(diffViewProvider as any).activeLineController = { setActiveLine: vi.fn(), clear: vi.fn() }
		;(diffViewProvider as any).fadedOverlayController = {
			updateOverlayAfterLine: vi.fn(),
			addLines: vi.fn(),
			clear: vi.fn(),
		}
	})





  __testAugmentVitest_dd82fd589c6a.it("reset_clears_internal_state_and_calls_closeAllDiffViews_round_011_pass_02", async () => {
  	// Arrange: populate many internal fields
  	;(diffViewProvider as any).editType = "modify"
  	;(diffViewProvider as any).isEditing = true
  	;(diffViewProvider as any).originalContent = "orig"
  	;(diffViewProvider as any).createdDirs = ["/a","/a/b"]
  	;(diffViewProvider as any).documentWasOpen = true
  	;(diffViewProvider as any).activeDiffEditor = { dummy: true } as any
  	;(diffViewProvider as any).fadedOverlayController = { clear: __testAugmentVitest_dd82fd589c6a.vi.fn() } as any
  	;(diffViewProvider as any).activeLineController = { clear: __testAugmentVitest_dd82fd589c6a.vi.fn() } as any
  	;(diffViewProvider as any).streamedLines = ["a","b"]
  	;(diffViewProvider as any).preDiagnostics = [[{ uri: { fsPath: "/x" } }, []]]

  	// Spy on closeAllDiffViews to ensure it's invoked by reset
  	;(diffViewProvider as any).closeAllDiffViews = __testAugmentVitest_dd82fd589c6a.vi.fn().mockResolvedValue(undefined)

  	// Act
  	await diffViewProvider.reset()

  	// Assert: internal fields are cleared/reset
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).editType).toBeUndefined()
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).isEditing).toBe(false)
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).originalContent).toBeUndefined()
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).createdDirs).toEqual([])
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).documentWasOpen).toBe(false)
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).activeDiffEditor).toBeUndefined()
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).fadedOverlayController).toBeUndefined()
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).activeLineController).toBeUndefined()
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).streamedLines).toEqual([])
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).preDiagnostics).toEqual([])
  	// And closeAllDiffViews was invoked
  	__testAugmentVitest_dd82fd589c6a.expect((diffViewProvider as any).closeAllDiffViews).toHaveBeenCalled()
  })
})

import * as __testAugmentVitest_dd82fd589c6a from "vitest";

const __testAugmentLoadTarget_03070e9065c4 = async () => {
  __testAugmentVitest_dd82fd589c6a.vi.doUnmock("../DiffViewProvider.js");
  __testAugmentVitest_dd82fd589c6a.vi.resetModules();
  return import("../DiffViewProvider.js");
};
