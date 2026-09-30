// npx vitest core/config/__tests__/CustomModesManager.spec.ts

import type { Mock } from "vitest"

import * as path from "path"
import * as fs from "fs/promises"

import * as yaml from "yaml"
import * as vscode from "vscode"

import type { ModeConfig } from "@roo-code/types"

import { fileExistsAtPath } from "../../../utils/fs"
import { getWorkspacePath, arePathsEqual } from "../../../utils/path"
import { GlobalFileNames } from "../../../shared/globalFileNames"

import { CustomModesManager } from "../CustomModesManager"

vi.mock("vscode", () => ({
	workspace: {
		workspaceFolders: [],
		onDidSaveTextDocument: vi.fn(),
		createFileSystemWatcher: vi.fn(),
	},
	window: {
		showErrorMessage: vi.fn(),
	},
}))

vi.mock("fs/promises", () => ({
	mkdir: vi.fn(),
	readFile: vi.fn(),
	writeFile: vi.fn(),
	stat: vi.fn(),
	readdir: vi.fn(),
	rm: vi.fn(),
}))

vi.mock("../../../utils/fs")
vi.mock("../../../utils/path")

describe("CustomModesManager", () => {
	let manager: CustomModesManager
	let mockContext: vscode.ExtensionContext
	let mockOnUpdate: Mock
	let mockWorkspaceFolders: { uri: { fsPath: string } }[]

	// Use path.sep to ensure correct path separators for the current platform
	const mockStoragePath = `${path.sep}mock${path.sep}settings`
	const mockSettingsPath = path.join(mockStoragePath, "settings", GlobalFileNames.customModes)
	const mockWorkspacePath = path.resolve("/mock/workspace")
	const mockRoomodes = path.join(mockWorkspacePath, ".roomodes")

	beforeEach(() => {
		mockOnUpdate = vi.fn()
		mockContext = {
			globalState: {
				get: vi.fn(),
				update: vi.fn(),
				keys: vi.fn(() => []),
				setKeysForSync: vi.fn(),
			},
			globalStorageUri: {
				fsPath: mockStoragePath,
			},
		} as unknown as vscode.ExtensionContext

		// mockWorkspacePath is now defined at the top level
		mockWorkspaceFolders = [{ uri: { fsPath: mockWorkspacePath } }]
		;(vscode.workspace as any).workspaceFolders = mockWorkspaceFolders
		;(vscode.workspace.onDidSaveTextDocument as Mock).mockReturnValue({ dispose: vi.fn() })
		;(getWorkspacePath as Mock).mockReturnValue(mockWorkspacePath)
		;(fileExistsAtPath as Mock).mockImplementation(async (path: string) => {
			return path === mockSettingsPath || path === mockRoomodes
		})
		;(fs.mkdir as Mock).mockResolvedValue(undefined)
		;(fs.writeFile as Mock).mockResolvedValue(undefined)
		;(fs.stat as Mock).mockResolvedValue({ isDirectory: () => true })
		;(fs.readdir as Mock).mockResolvedValue([])
		;(fs.rm as Mock).mockResolvedValue(undefined)
		;(fs.readFile as Mock).mockImplementation(async (path: string) => {
			if (path === mockSettingsPath) {
				return yaml.stringify({ customModes: [] })
			}

			throw new Error("File not found")
		})

		manager = new CustomModesManager(mockContext, mockOnUpdate)
	})

	afterEach(() => {
		vi.clearAllMocks()
	})





	describe("updateModesInFile", () => {

	  __testAugmentVitest_ea636a51c20b.it("exportModeWithRules_mergesCustomPrompts_round_013_pass_02", async () => {
	  	// Provide a custom mode in .roomodes and ensure there are no rules files
	  	const roomodesContent = {
	  		customModes: [
	  			{ slug: 'test-export', name: 'OldName', roleDefinition: 'OldRole', groups: ['read'], customInstructions: 'OldInst' },
	  		],
	  	}

	  	;(fileExistsAtPath as any).mockImplementation(async (p: string) => p === mockRoomodes || p === mockSettingsPath)
	  	;(fs.readFile as any).mockImplementation(async (p: string) => {
	  		if (p === mockRoomodes) return yaml.stringify(roomodesContent)
	  		if (p === mockSettingsPath) return yaml.stringify({ customModes: [] })
	  		throw new Error('File not found')
	  	})

	  	// Make stat fail so the manager treats rules directory as not present (still a successful export)
	  	;(fs.stat as any).mockRejectedValue(new Error('no-dir'))

	  	const mgr = new CustomModesManager(mockContext, mockOnUpdate)

	  	const customPrompts = {
	  		roleDefinition: 'NewRole',
	  		description: 'NewDescription',
	  		whenToUse: 'When',
	  		customInstructions: 'NewInstructions',
	  	}

	  	const res = await mgr.exportModeWithRules('test-export', customPrompts)

	  	__testAugmentVitest_ea636a51c20b.expect(res.success).toBe(true)
	  	__testAugmentVitest_ea636a51c20b.expect(res.yaml).toContain('NewRole')
	  	__testAugmentVitest_ea636a51c20b.expect(res.yaml).toContain('NewDescription')
	  	__testAugmentVitest_ea636a51c20b.expect(res.yaml).toContain('NewInstructions')
	  })
	})


})

import * as __testAugmentVitest_ea636a51c20b from "vitest";

const __testAugmentLoadTarget_7c207ae8c838 = async () => {
  __testAugmentVitest_ea636a51c20b.vi.doUnmock("../CustomModesManager.js");
  __testAugmentVitest_ea636a51c20b.vi.resetModules();
  return import("../CustomModesManager.js");
};
