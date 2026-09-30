// npx vitest run src/services/checkpoints/__tests__/ShadowCheckpointService.spec.ts

import fs from "fs/promises"
import path from "path"
import os from "os"
import { EventEmitter } from "events"

import { simpleGit, SimpleGit } from "simple-git"

import { fileExistsAtPath } from "../../../utils/fs"
import * as fileSearch from "../../../services/search/file-search"

import { RepoPerTaskCheckpointService } from "../RepoPerTaskCheckpointService"

const tmpDir = path.join(os.tmpdir(), "CheckpointService")

const initWorkspaceRepo = async ({
	workspaceDir,
	userName = "Roo Code",
	userEmail = "support@roocode.com",
	testFileName = "test.txt",
	textFileContent = "Hello, world!",
}: {
	workspaceDir: string
	userName?: string
	userEmail?: string
	testFileName?: string
	textFileContent?: string
}) => {
	// Create a temporary directory for testing.
	await fs.mkdir(workspaceDir, { recursive: true })

	// Initialize git repo.
	const git = simpleGit(workspaceDir)
	await git.init()
	await git.addConfig("user.name", userName)
	await git.addConfig("user.email", userEmail)

	// Create test file.
	const testFile = path.join(workspaceDir, testFileName)
	await fs.writeFile(testFile, textFileContent)

	// Create initial commit.
	await git.add(".")
	await git.commit("Initial commit")!

	return { git, testFile }
}


describe("worktree path comparison", () => {

  __testAugmentVitest_83160e95320a.test("deleteTask_logs_error_on_delete_failure_round_025_pass_03", async () => {
  	const vi = __testAugmentVitest_83160e95320a.vi

  	// Mock simple-git so createSanitizedGit returns a dummy git; do this before loading the module.
  	vi.doMock("simple-git", () => ({
  		__esModule: true,
  		default: (options: any) => ({
  			env: (e: any) => undefined,
  			version: async () => "vX.Y.Z",
  		}),
  	}))

  	const errorSpy = vi.spyOn(console, "error")

  	const { ShadowCheckpointService } = await __testAugmentLoadTarget_6a2f5ed8e785()

  	// Make deleteBranch return false to exercise the failure branch that calls console.error
  	vi.spyOn(ShadowCheckpointService, "deleteBranch").mockResolvedValue(false)

  	await ShadowCheckpointService.deleteTask({ taskId: "failtask", globalStorageDir: "/tmp/g2", workspaceDir: "/tmp/w2" })

  	__testAugmentVitest_83160e95320a.expect(errorSpy.mock.calls.some((c) => String(c[0]).includes("failed to delete branch")) ).toBe(true)

  	// Cleanup
  	errorSpy.mockRestore()
  	vi.restoreAllMocks()
  })
})

import * as __testAugmentVitest_83160e95320a from "vitest";

const __testAugmentLoadTarget_6a2f5ed8e785 = async () => {
  __testAugmentVitest_83160e95320a.vi.doUnmock("../ShadowCheckpointService.js");
  __testAugmentVitest_83160e95320a.vi.resetModules();
  return import("../ShadowCheckpointService.js");
};
