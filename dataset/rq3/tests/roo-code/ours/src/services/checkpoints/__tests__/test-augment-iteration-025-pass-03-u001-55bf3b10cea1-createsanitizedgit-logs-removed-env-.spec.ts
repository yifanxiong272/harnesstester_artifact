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

  __testAugmentVitest_83160e95320a.test("createSanitizedGit_logs_removed_env_vars_round_025_pass_03", async () => {
  	const vi = __testAugmentVitest_83160e95320a.vi
  	// Arrange: set some git env vars that should be removed and a normal env var that should remain
  	process.env.GIT_DIR = "/tmp/fakegit/.git"
  	process.env.GIT_WORK_TREE = "/tmp/fake-worktree"
  	process.env.ROO_TEST_VAR = "keep-me"

  	// Mock simple-git so createSanitizedGit uses our fake git object and we can observe env() and version()
  	vi.doMock("simple-git", () => ({
  		__esModule: true,
  		default: (options: any) => {
  			let lastEnv: Record<string, string> | null = null
  			return {
  				env: (envObj: Record<string, string>) => {
  					lastEnv = envObj
  					return undefined
  				},
  				version: async () => "fake-git-1.2.3",
  			}
  		},
  	}))

  	// Spy on console.log so we can assert messages produced by createSanitizedGit
  	const logSpy = vi.spyOn(console, "log")

  	// Load the target after registering mocks
  	const { ShadowCheckpointService } = await __testAugmentLoadTarget_6a2f5ed8e785()

  	// Spy on the static deleteBranch so deleteTask completes quickly without needing a real git branch deletion
  	vi.spyOn(ShadowCheckpointService, "deleteBranch").mockResolvedValue(true)

  	// Act: call deleteTask which internally calls createSanitizedGit
  	await ShadowCheckpointService.deleteTask({ taskId: "tid-1", globalStorageDir: "/tmp/global", workspaceDir: "/tmp/workspace" })

  	// Assert: console.log should have been called with a message about removed git env vars and about creating the git instance
  	const logged = logSpy.mock.calls.map((c) => String(c[0]))
  	__testAugmentVitest_83160e95320a.expect(logged.some((m) => m.includes("[createSanitizedGit] Removed git environment variables for checkpoint isolation"))).toBe(true)
  	__testAugmentVitest_83160e95320a.expect(logged.some((m) => m.includes("[createSanitizedGit] Created git instance for baseDir:"))).toBe(true)

  	// Cleanup
  	logSpy.mockRestore()
  	vi.restoreAllMocks()
  	delete process.env.GIT_DIR
  	delete process.env.GIT_WORK_TREE
  	delete process.env.ROO_TEST_VAR
  })
})

import * as __testAugmentVitest_83160e95320a from "vitest";

const __testAugmentLoadTarget_6a2f5ed8e785 = async () => {
  __testAugmentVitest_83160e95320a.vi.doUnmock("../ShadowCheckpointService.js");
  __testAugmentVitest_83160e95320a.vi.resetModules();
  return import("../ShadowCheckpointService.js");
};
