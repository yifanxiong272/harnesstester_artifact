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

  __testAugmentVitest_83160e95320a.test("deleteBranch_current_branch_error_round_025", async () => {
  	// Mock p-wait-for so the function runs deterministically.
  	__testAugmentVitest_83160e95320a.vi.doMock("p-wait-for", () => ({
  		__esModule: true,
  		default: async (checkFn: any) => {
  			// Call the check function once, then resolve (we just need it to run).
  			await checkFn()
  			return
  		},
  	}))

  	const { ShadowCheckpointService } = await __testAugmentLoadTarget_6a2f5ed8e785()

  	// Simulate git operations that throw during the current-branch deletion flow.
  	let currentBranch = "roo-err"
  	const branchName = "roo-err"

  	const gitMock = {
  		branchLocal: async () => ({ all: [branchName, "main"] }),
  		revparse: async (args?: any) => {
  			if (Array.isArray(args) && args[0] === "--abbrev-ref") return currentBranch
  			return "shaErr"
  		},
  		getConfig: async () => ({ value: "/tmp/workspace" }),
  		raw: async () => undefined,
  		reset: async () => { throw new Error("reset failed") },
  		clean: async () => undefined,
  		checkout: async () => undefined,
  		branch: async () => undefined,
  		addConfig: async () => undefined,
  	}

  	const res = await ShadowCheckpointService.deleteBranch(gitMock as any, branchName)
  	__testAugmentVitest_83160e95320a.expect(res).toBe(false)
  })
})

import * as __testAugmentVitest_83160e95320a from "vitest";

const __testAugmentLoadTarget_6a2f5ed8e785 = async () => {
  __testAugmentVitest_83160e95320a.vi.doUnmock("../ShadowCheckpointService.js");
  __testAugmentVitest_83160e95320a.vi.resetModules();
  return import("../ShadowCheckpointService.js");
};
