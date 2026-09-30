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

  __testAugmentVitest_83160e95320a.test("hash_workspace_dir_round_025", async () => {
  	// Load the target module (no special dependency mocks required for this static util).
  	const { ShadowCheckpointService } = await __testAugmentLoadTarget_6a2f5ed8e785()

  	const v1 = ShadowCheckpointService.hashWorkspaceDir("/some/arbitrary/workspace/path")
  	const v2 = ShadowCheckpointService.hashWorkspaceDir("/some/arbitrary/workspace/path")

  	// Deterministic: same input -> same 8-hex string
  	__testAugmentVitest_83160e95320a.expect(typeof v1).toBe("string")
  	__testAugmentVitest_83160e95320a.expect(v1).toMatch(/^[0-9a-f]{8}$/)
  	__testAugmentVitest_83160e95320a.expect(v1).toBe(v2)
  })
})

import * as __testAugmentVitest_83160e95320a from "vitest";

const __testAugmentLoadTarget_6a2f5ed8e785 = async () => {
  __testAugmentVitest_83160e95320a.vi.doUnmock("../ShadowCheckpointService.js");
  __testAugmentVitest_83160e95320a.vi.resetModules();
  return import("../ShadowCheckpointService.js");
};
