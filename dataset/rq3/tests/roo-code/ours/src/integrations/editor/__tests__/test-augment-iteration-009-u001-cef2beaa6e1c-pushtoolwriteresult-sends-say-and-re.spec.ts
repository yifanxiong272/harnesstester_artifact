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





  __testAugmentVitest_dd82fd589c6a.it("pushToolWriteResult sends say and returns JSON_round_009", async () => {
  	// Create a minimal mock Task with a spyable say method
  	const mockTask: any = { say: __testAugmentVitest_dd82fd589c6a.vi.fn().mockResolvedValue(undefined) }

  	const provider = new DiffViewProvider("/cwd", mockTask)
  	// Set the internal state that triggers sending user_feedback_diff and including fields in result
  	;(provider as any).relPath = "path/to/file.txt"
  	;(provider as any).userEdits = "--- a\n+++ b\n@@ -1 +1 @@\n-foo\n+bar\n"
  	;(provider as any).newProblemsMessage = "Some problems"

  	const out = await provider.pushToolWriteResult(mockTask, "/cwd", true)

  	// The task.say should have been called with the user_feedback_diff tool and a JSON payload
  	__testAugmentVitest_dd82fd589c6a.expect(mockTask.say).toHaveBeenCalledWith(
  		"user_feedback_diff",
  		__testAugmentVitest_dd82fd589c6a.expect.any(String),
  	)

  	// The returned string should parse to an object containing the expected keys when userEdits present
  	const parsed = JSON.parse(out)
  	__testAugmentVitest_dd82fd589c6a.expect(parsed.path).toBe("path/to/file.txt")
  	__testAugmentVitest_dd82fd589c6a.expect(parsed.operation).toBe("created")
  	__testAugmentVitest_dd82fd589c6a.expect(parsed.user_edits).toBe("--- a\n+++ b\n@@ -1 +1 @@\n-foo\n+bar\n")
  	__testAugmentVitest_dd82fd589c6a.expect(parsed.problems).toBe("Some problems")
  })
})

import * as __testAugmentVitest_dd82fd589c6a from "vitest";

const __testAugmentLoadTarget_03070e9065c4 = async () => {
  __testAugmentVitest_dd82fd589c6a.vi.doUnmock("../DiffViewProvider.js");
  __testAugmentVitest_dd82fd589c6a.vi.resetModules();
  return import("../DiffViewProvider.js");
};
