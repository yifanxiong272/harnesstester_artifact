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

  __testAugmentVitest_83160e95320a.test("deleteBranch_nonexistent_branch_round_025", async () => {
  	// Load the target module. No global dependency mocks necessary because we pass a mock git object.
  	const { ShadowCheckpointService } = await __testAugmentLoadTarget_6a2f5ed8e785()

  	// Simulate a repository that does not contain the target branch.
  	const gitMock = {
  		branchLocal: async () => ({ all: ["main", "develop"] }),
  		// revparse may be called elsewhere; provide a noop implementation.
  		revparse: async () => "main",
  	}

  	const result = await ShadowCheckpointService.deleteBranch(gitMock as any, "roo-nonexistent-branch")
  	__testAugmentVitest_83160e95320a.expect(result).toBe(false)
  })
})

import * as __testAugmentVitest_83160e95320a from "vitest";

const __testAugmentLoadTarget_6a2f5ed8e785 = async () => {
  __testAugmentVitest_83160e95320a.vi.doUnmock("../ShadowCheckpointService.js");
  __testAugmentVitest_83160e95320a.vi.resetModules();
  return import("../ShadowCheckpointService.js");
};
