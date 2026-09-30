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

  __testAugmentVitest_83160e95320a.test("deleteBranch_current_branch_success_round_025", async () => {
  	// Mock p-wait-for to avoid real polling; resolve after a single check invocation.
  	__testAugmentVitest_83160e95320a.vi.doMock("p-wait-for", () => ({
  		__esModule: true,
  		default: async (checkFn: any) => {
  			// Call the provided check function once; if it returns truthy, resolve.
  			// This keeps the test deterministic and fast.
  			const ok = await checkFn()
  			if (ok) return
  			throw new Error("p-wait-for: condition not satisfied")
  		},
  	}))

  	// Load the target module AFTER registering the mock.
  	const { ShadowCheckpointService } = await __testAugmentLoadTarget_6a2f5ed8e785()

  	// Simulate a git instance where the current branch is the one to delete.
  	let currentBranch = "roo-42"
  	const branchName = "roo-42"

  	const gitMock = {
  		branchLocal: async () => ({ all: ["main", branchName] }),
  		revparse: async (args?: any) => {
  			// Support revparse(["--abbrev-ref","HEAD"]) -> currentBranch
  			if (Array.isArray(args) && args[0] === "--abbrev-ref") return currentBranch
  			return "sha123"
  		},
  		getConfig: async () => ({ value: "/tmp/workspace" }),
  		raw: async () => undefined,
  		reset: async () => undefined,
  		clean: async () => undefined,
  		checkout: async () => {
  			// Simulate checkout to default branch
  			currentBranch = "main"
  			return undefined
  		},
  		branch: async () => undefined,
  		addConfig: async () => undefined,
  	}

  	const res = await ShadowCheckpointService.deleteBranch(gitMock as any, branchName)
  	__testAugmentVitest_83160e95320a.expect(res).toBe(true)
  })
})

import * as __testAugmentVitest_83160e95320a from "vitest";

const __testAugmentLoadTarget_6a2f5ed8e785 = async () => {
  __testAugmentVitest_83160e95320a.vi.doUnmock("../ShadowCheckpointService.js");
  __testAugmentVitest_83160e95320a.vi.resetModules();
  return import("../ShadowCheckpointService.js");
};
