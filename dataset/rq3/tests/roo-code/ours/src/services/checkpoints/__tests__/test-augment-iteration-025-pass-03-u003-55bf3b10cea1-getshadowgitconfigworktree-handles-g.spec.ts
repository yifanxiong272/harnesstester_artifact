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

  __testAugmentVitest_83160e95320a.test("getShadowGitConfigWorktree_handles_getConfig_throw_round_025_pass_03", async () => {
  	const { ShadowCheckpointService } = await __testAugmentLoadTarget_6a2f5ed8e785()

  	class Concrete extends ShadowCheckpointService {}

  	// Capture logs
  	const logs: string[] = []
  	const svc = new Concrete("t-worktree", "/tmp/checkpoints-worktree", "/tmp/workspace-worktree", (m: string) => logs.push(m))

  	// Mock git whose getConfig throws
  	const gitMock = {
  		getConfig: async (key: string) => {
  			throw new Error("config-failure")
  		},
  	}

  	// Call the private getShadowGitConfigWorktree and assert it returns undefined and logs the failure
  	const result = await (svc as any).getShadowGitConfigWorktree(gitMock)
  	__testAugmentVitest_83160e95320a.expect(result).toBeUndefined()
  	__testAugmentVitest_83160e95320a.expect(logs.some((l) => l.includes("failed to get core.worktree") && l.includes("config-failure"))).toBe(true)
  })
})

import * as __testAugmentVitest_83160e95320a from "vitest";

const __testAugmentLoadTarget_6a2f5ed8e785 = async () => {
  __testAugmentVitest_83160e95320a.vi.doUnmock("../ShadowCheckpointService.js");
  __testAugmentVitest_83160e95320a.vi.resetModules();
  return import("../ShadowCheckpointService.js");
};
